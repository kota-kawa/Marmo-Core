// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "lib/forge-std/src/Test.sol";
import {MultiSigTreasury} from "../src/MultiSigTreasury.sol";
import {CampaignFactory} from "../src/CampaignFactory.sol";
import {AgentRegistry} from "../src/AgentRegistry.sol";
import {PlatformFeeManager} from "../src/PlatformFeeManager.sol";

/**
 * @title MultiSigTreasuryTest
 * @notice Comprehensive tests for multi-sig treasury functionality
 */
contract MultiSigTreasuryTest is Test {
    MultiSigTreasury public treasury;
    CampaignFactory public factory;
    AgentRegistry public registry;
    PlatformFeeManager public feeManager;

    address public genesisBot;
    address public feeManagerAddress;
    address public agentOwner;
    address public thirdSigner;
    address public recipient;

    uint256 public constant INITIAL_BALANCE = 10 ether;
    uint256 public constant CAMPAIGN_ID = 1;

    function setUp() public {
        // Setup accounts
        genesisBot = makeAddr("genesisBot");
        feeManagerAddress = makeAddr("feeManager");
        agentOwner = makeAddr("agentOwner");
        thirdSigner = makeAddr("thirdSigner");
        recipient = makeAddr("recipient");

        // Deploy contracts
        vm.startPrank(genesisBot);
        
        registry = new AgentRegistry(0.1 ether);
        feeManager = new PlatformFeeManager(feeManagerAddress);
        treasury = new MultiSigTreasury(genesisBot, feeManagerAddress);
        factory = new CampaignFactory(
            address(registry),
            address(feeManager),
            address(treasury)
        );

        // Authorize factory
        treasury.setAuthorizedFactory(address(factory));

        vm.stopPrank();

        // Fund accounts (agentOwner needs extra for registration fee)
        vm.deal(agentOwner, INITIAL_BALANCE + 1 ether);
        vm.deal(genesisBot, INITIAL_BALANCE);
        vm.deal(thirdSigner, INITIAL_BALANCE);
        vm.deal(address(this), 400 ether);
    }

    function test_CreateTreasury() public {
        // Register agent first (pay registration fee)
        vm.prank(agentOwner);
        registry.register{value: 0.1 ether}("ipfs://metadata", "@agent");

        // Create campaign (which creates treasury)
        vm.prank(agentOwner);
        uint256 campaignId = factory.createCampaign(
            1, // agent ID
            100 ether, // goal
            30 days, // duration
            "ipfs://metadata",
            thirdSigner
        );

        // Verify treasury was created
        address[] memory signers = factory.getTreasurySigners(campaignId);
        assertEq(signers.length, 3, "Should have 3 signers");
        assertEq(signers[0], genesisBot, "Genesis should be first signer");
        assertEq(signers[1], agentOwner, "Agent owner should be second signer");
        assertEq(signers[2], thirdSigner, "Third signer should be third");
    }

    function test_DepositToTreasury() public {
        // Setup treasury
        vm.prank(agentOwner);
        registry.register{value: 0.1 ether}("ipfs://metadata", "@agent");

        vm.prank(agentOwner);
        uint256 campaignId = factory.createCampaign(
            1,
            100 ether,
            30 days,
            "ipfs://metadata",
            address(0)
        );

        // Deposit funds
        uint256 depositAmount = 5 ether;
        vm.prank(agentOwner);
        factory.depositToTreasury{value: depositAmount}(campaignId);

        uint256 balance = factory.getTreasuryBalance(campaignId);
        assertEq(balance, depositAmount, "Treasury should have deposited amount");
    }

    function test_ProposeAndConfirmSpend() public {
        // Setup
        vm.prank(agentOwner);
        registry.register{value: 0.1 ether}("ipfs://metadata", "@agent");

        vm.prank(agentOwner);
        uint256 campaignId = factory.createCampaign(
            1,
            100 ether,
            30 days,
            "ipfs://metadata",
            address(0)
        );

        // Contribute funds
        vm.prank(address(this));
        factory.contribute{value: 360 ether}(campaignId);

        // Propose spend
        uint256 spendAmount = 350e18; // $350 worth (requires multi-sig)
        vm.prank(agentOwner);
        uint256 proposalId = factory.proposeMultiSigSpend(
            campaignId,
            recipient,
            spendAmount,
            "Test spend"
        );

        // Confirm as Genesis bot
        vm.prank(genesisBot);
        treasury.confirmProposal(campaignId, proposalId);

        // Confirm as agent owner
        vm.prank(agentOwner);
        treasury.confirmProposal(campaignId, proposalId);

        // Check recipient received funds
        assertEq(recipient.balance, spendAmount, "Recipient should receive funds");
    }

    function test_RemoveGenesisSigner() public {
        // Setup
        vm.prank(agentOwner);
        registry.register{value: 0.1 ether}("ipfs://metadata", "@agent");

        vm.prank(agentOwner);
        uint256 campaignId = factory.createCampaign(
            1,
            100 ether,
            30 days,
            "ipfs://metadata",
            thirdSigner
        );

        // Deposit funds directly to treasury (fee is % of treasury funds)
        vm.prank(agentOwner);
        factory.depositToTreasury{value: 10 ether}(campaignId);

        uint256 initialFeeManagerBalance = feeManagerAddress.balance;

        // Calculate removal fee (1.5% = 150 bps)
        uint256 removalFee = (10 ether * 150) / 10000; // 0.15 ETH

        // Remove Genesis signer
        vm.prank(agentOwner);
        factory.removeGenesisSigner{value: removalFee}(campaignId, 150);

        // Verify Genesis removed
        address[] memory signers = factory.getTreasurySigners(campaignId);
        assertEq(signers.length, 2, "Should have 2 signers after removal");

        // Verify fee paid
        assertEq(
            feeManagerAddress.balance - initialFeeManagerBalance,
            removalFee,
            "Fee manager should receive removal fee"
        );
    }

    function test_SmallWithdrawNoMultisig() public {
        // Setup
        vm.prank(agentOwner);
        registry.register{value: 0.1 ether}("ipfs://metadata", "@agent");

        vm.prank(agentOwner);
        uint256 campaignId = factory.createCampaign(
            1,
            100 ether,
            30 days,
            "ipfs://metadata",
            address(0)
        );

        // Contribute to campaign
        vm.prank(address(this));
        factory.contribute{value: 5 ether}(campaignId);

        uint256 smallAmount = 0.1 ether; // Less than $300 threshold

        // Withdraw without multi-sig
        vm.prank(agentOwner);
        factory.withdrawFunds(campaignId, smallAmount);

        // Expect balance: Initial (11) - Reg Fee (0.1) + Withdraw (0.1) = 11
        assertEq(agentOwner.balance, INITIAL_BALANCE + 1 ether, "Should receive small withdrawal");
    }

    function test_RevertLargeWithdrawWithoutMultisig() public {
        // Setup
        vm.prank(agentOwner);
        registry.register{value: 0.1 ether}("ipfs://metadata", "@agent");

        vm.prank(agentOwner);
        uint256 campaignId = factory.createCampaign(
            1,
            100 ether,
            30 days,
            "ipfs://metadata",
            address(0)
        );

        // Contribute
        vm.prank(address(this));
        factory.contribute{value: 360 ether}(campaignId);

        uint256 largeAmount = 350e18; // More than $300 threshold

        // Should revert
        vm.prank(agentOwner);
        vm.expectRevert("Use multi-sig for large withdrawals");
        factory.withdrawFunds(campaignId, largeAmount);
    }

    function test_RevertInvalidRemovalFee() public {
        // Setup
        vm.prank(agentOwner);
        registry.register{value: 0.1 ether}("ipfs://metadata", "@agent");

        vm.prank(agentOwner);
        uint256 campaignId = factory.createCampaign(
            1,
            100 ether,
            30 days,
            "ipfs://metadata",
            address(0)
        );

        // Try to remove with fee below 1% (50 bps)
        vm.prank(agentOwner);
        vm.expectRevert(); // Should revert with InvalidFee
        factory.removeGenesisSigner{value: 0.1 ether}(campaignId, 50);

        // Try to remove with fee above 2% (300 bps)
        vm.prank(agentOwner);
        vm.expectRevert(); // Should revert with InvalidFee
        factory.removeGenesisSigner{value: 0.5 ether}(campaignId, 300);
    }

    function test_ProposalExpiration() public {
        // Setup
        vm.prank(agentOwner);
        registry.register{value: 0.1 ether}("ipfs://metadata", "@agent");

        vm.prank(agentOwner);
        uint256 campaignId = factory.createCampaign(
            1,
            100 ether,
            30 days,
            "ipfs://metadata",
            address(0)
        );

        vm.prank(address(this));
        factory.contribute{value: 360 ether}(campaignId);

        // Propose spend
        vm.prank(agentOwner);
        uint256 proposalId = factory.proposeMultiSigSpend(
            campaignId,
            recipient,
            350e18,
            "Test spend"
        );

        // Fast forward 8 days
        vm.warp(block.timestamp + 8 days);

        // Try to confirm (should revert)
        vm.prank(genesisBot);
        vm.expectRevert(); // Should revert with ProposalExpired
        treasury.confirmProposal(campaignId, proposalId);
    }

    function test_RevertNonSignerConfirmation() public {
        // Setup
        vm.prank(agentOwner);
        registry.register{value: 0.1 ether}("ipfs://metadata", "@agent");

        vm.prank(agentOwner);
        uint256 campaignId = factory.createCampaign(
            1,
            100 ether,
            30 days,
            "ipfs://metadata",
            address(0)
        );

        vm.prank(address(this));
        factory.contribute{value: 360 ether}(campaignId);

        address nonSigner = makeAddr("nonSigner");

        // Propose spend
        vm.prank(agentOwner);
        uint256 proposalId = factory.proposeMultiSigSpend(
            campaignId,
            recipient,
            350e18,
            "Test spend"
        );

        // Non-signer tries to confirm
        vm.prank(nonSigner);
        vm.expectRevert(); // Should revert with NotSigner
        treasury.confirmProposal(campaignId, proposalId);
    }
}
