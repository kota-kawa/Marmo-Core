// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/AgentRegistry.sol";
import "../src/PlatformFeeManager.sol";
import "../src/MultiSigTreasury.sol";
import "../src/CampaignFactory.sol";
import "../src/RecurringDonations.sol";

/**
 * @title RecurringDonationsTest
 * @notice Tests for the RecurringDonations contract
 */
contract RecurringDonationsTest is Test {
    AgentRegistry public agentRegistry;
    PlatformFeeManager public feeManager;
    MultiSigTreasury public multiSigTreasury;
    CampaignFactory public campaignFactory;
    RecurringDonations public recurring;

    address public owner = address(this);
    address public donor = address(0xD00D0D);
    address public agent = address(0xA6E47);
    address public thirdSigner = address(0x3333);

    uint256 public campaignId;

    function setUp() public {
        // Deploy infrastructure
        feeManager = new PlatformFeeManager(owner);
        agentRegistry = new AgentRegistry(0.1 ether);
        agentRegistry.setPlatformFeeManager(address(feeManager));
        multiSigTreasury = new MultiSigTreasury(owner, address(feeManager));
        campaignFactory = new CampaignFactory(
            address(agentRegistry),
            address(feeManager),
            address(multiSigTreasury)
        );

        // Deploy RecurringDonations
        recurring = new RecurringDonations(address(campaignFactory));

        // Register an agent
        vm.deal(agent, 10 ether);
        vm.prank(agent);
        agentRegistry.register{value: 0.1 ether}("ipfs://agent-meta", "@testbot");

        // Create a campaign (agent ID = 1)
        vm.prank(agent);
        campaignId = campaignFactory.createCampaign(1, 10 ether, 30 days, "ipfs://campaign", thirdSigner);

        // Fund the donor
        vm.deal(donor, 100 ether);
    }

    // ============ Deposit & Withdraw ============

    function test_deposit() public {
        vm.prank(donor);
        recurring.deposit{value: 5 ether}();
        assertEq(recurring.balances(donor), 5 ether);
    }

    function test_withdraw() public {
        vm.prank(donor);
        recurring.deposit{value: 5 ether}();

        uint256 balBefore = donor.balance;
        vm.prank(donor);
        recurring.withdraw(2 ether);

        assertEq(recurring.balances(donor), 3 ether);
        assertEq(donor.balance, balBefore + 2 ether);
    }

    function test_withdrawInsufficientReverts() public {
        vm.prank(donor);
        recurring.deposit{value: 1 ether}();

        vm.prank(donor);
        vm.expectRevert();
        recurring.withdraw(2 ether);
    }

    // ============ Subscriptions ============

    function test_createSubscription() public {
        vm.prank(donor);
        recurring.deposit{value: 10 ether}();

        vm.prank(donor);
        uint256 subId = recurring.createSubscription(
            campaignId,
            0.5 ether,   // 0.5 ETH per period
            7 days,       // weekly
            4             // max 4 donations
        );

        assertEq(subId, 1);

        (
            address subDonor,
            uint256 subCampaignId,
            uint256 amount,
            uint256 interval,
            ,
            uint256 totalExecuted,
            uint256 maxExecutions,
            bool active
        ) = recurring.subscriptions(subId);

        assertEq(subDonor, donor);
        assertEq(subCampaignId, campaignId);
        assertEq(amount, 0.5 ether);
        assertEq(interval, 7 days);
        assertEq(totalExecuted, 0);
        assertEq(maxExecutions, 4);
        assertTrue(active);
    }

    function test_createSubscriptionInvalidIntervalReverts() public {
        vm.prank(donor);
        vm.expectRevert();
        recurring.createSubscription(campaignId, 0.5 ether, 30 minutes, 0);
    }

    function test_createSubscriptionInvalidAmountReverts() public {
        vm.prank(donor);
        vm.expectRevert();
        recurring.createSubscription(campaignId, 0, 7 days, 0);
    }

    // ============ Execution ============

    function test_executeSubscription() public {
        // Setup
        vm.prank(donor);
        recurring.deposit{value: 10 ether}();

        vm.prank(donor);
        uint256 subId = recurring.createSubscription(campaignId, 1 ether, 1 days, 0);

        // Execute immediately (first execution is allowed right away)
        recurring.execute(subId);

        assertEq(recurring.balances(donor), 9 ether);
        (,,,,, uint256 totalExecuted,,) = recurring.subscriptions(subId);
        assertEq(totalExecuted, 1);
    }

    function test_executeTooEarlyReverts() public {
        vm.prank(donor);
        recurring.deposit{value: 10 ether}();

        vm.prank(donor);
        uint256 subId = recurring.createSubscription(campaignId, 1 ether, 1 days, 0);

        // Execute first one
        recurring.execute(subId);

        // Try again immediately - should revert
        vm.expectRevert();
        recurring.execute(subId);

        // Fast forward and execute again
        vm.warp(block.timestamp + 1 days);
        recurring.execute(subId);

        (,,,,, uint256 totalExecuted,,) = recurring.subscriptions(subId);
        assertEq(totalExecuted, 2);
    }

    function test_executeMaxReached() public {
        vm.prank(donor);
        recurring.deposit{value: 10 ether}();

        vm.prank(donor);
        uint256 subId = recurring.createSubscription(campaignId, 1 ether, 1 hours, 2);

        // Execute twice
        recurring.execute(subId);
        vm.warp(block.timestamp + 1 hours);
        recurring.execute(subId);

        // Third should revert
        vm.warp(block.timestamp + 1 hours);
        vm.expectRevert();
        recurring.execute(subId);

        // Subscription should be inactive
        (,,,,,,,bool active) = recurring.subscriptions(subId);
        assertFalse(active);
    }

    function test_executeInsufficientBalanceCancels() public {
        vm.prank(donor);
        recurring.deposit{value: 0.5 ether}();

        vm.prank(donor);
        uint256 subId = recurring.createSubscription(campaignId, 1 ether, 1 hours, 0);

        // Should revert because donor doesn't have enough balance
        vm.expectRevert();
        recurring.execute(subId);
    }

    // ============ Cancel ============

    function test_cancel() public {
        vm.prank(donor);
        recurring.deposit{value: 10 ether}();

        vm.prank(donor);
        uint256 subId = recurring.createSubscription(campaignId, 1 ether, 1 days, 0);

        vm.prank(donor);
        recurring.cancel(subId);

        (,,,,,,,bool active) = recurring.subscriptions(subId);
        assertFalse(active);
    }

    function test_cancelNotOwnerReverts() public {
        vm.prank(donor);
        recurring.deposit{value: 10 ether}();

        vm.prank(donor);
        uint256 subId = recurring.createSubscription(campaignId, 1 ether, 1 days, 0);

        vm.prank(address(0xBAAD));
        vm.expectRevert();
        recurring.cancel(subId);
    }

    // ============ View Functions ============

    function test_isExecutable() public {
        vm.prank(donor);
        recurring.deposit{value: 10 ether}();

        vm.prank(donor);
        uint256 subId = recurring.createSubscription(campaignId, 1 ether, 1 days, 0);

        assertTrue(recurring.isExecutable(subId));

        recurring.execute(subId);

        // Not executable immediately after
        assertFalse(recurring.isExecutable(subId));

        // Executable after interval
        vm.warp(block.timestamp + 1 days);
        assertTrue(recurring.isExecutable(subId));
    }

    function test_getExecutableSubscriptions() public {
        vm.prank(donor);
        recurring.deposit{value: 10 ether}();

        vm.prank(donor);
        recurring.createSubscription(campaignId, 1 ether, 1 days, 0);

        vm.prank(donor);
        recurring.createSubscription(campaignId, 0.5 ether, 7 days, 0);

        uint256[] memory executable = recurring.getExecutableSubscriptions(1, 3);
        assertEq(executable.length, 2);
    }

    function test_getDonorSubscriptions() public {
        vm.prank(donor);
        recurring.deposit{value: 10 ether}();

        vm.prank(donor);
        recurring.createSubscription(campaignId, 1 ether, 1 days, 0);

        vm.prank(donor);
        recurring.createSubscription(campaignId, 0.5 ether, 7 days, 5);

        uint256[] memory subs = recurring.getDonorSubscriptions(donor);
        assertEq(subs.length, 2);
        assertEq(subs[0], 1);
        assertEq(subs[1], 2);
    }

    // Allow receiving ETH refunds
    receive() external payable {}
}
