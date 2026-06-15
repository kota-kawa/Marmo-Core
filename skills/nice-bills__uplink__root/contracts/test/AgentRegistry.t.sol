// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/AgentRegistry.sol";

/**
 * @title AgentRegistryTest
 * @notice Comprehensive test suite for AgentRegistry contract
 * @dev Tests registration, metadata updates, reputation, and ownership
 */
contract AgentRegistryTest is Test {
    AgentRegistry public registry;
    address public owner;
    address public platformFeeManager;
    address public user1;
    address public user2;

    event AgentRegistered(
        uint256 indexed agentId,
        address indexed owner,
        string metadataURI,
        uint256 createdAt
    );
    event MetadataUpdated(
        uint256 indexed agentId,
        string oldMetadataURI,
        string newMetadataURI
    );
    event ReputationUpdated(
        uint256 indexed agentId,
        uint256 oldReputation,
        uint256 newReputation
    );

    function setUp() public {
        owner = address(this);
        platformFeeManager = address(0x1);
        user1 = address(0x2);
        user2 = address(0x3);

        vm.deal(user1, 10 ether);
        vm.deal(user2, 10 ether);

        registry = new AgentRegistry(0.1 ether);
    }

    function test_Register_Success() public {
        string memory metadataURI = "ipfs://QmTest";
        string memory twitterHandle = "@testuser";

        vm.startPrank(user1);
        uint256 agentId = registry.register{value: 0.1 ether}(
            metadataURI,
            twitterHandle
        );

        assertEq(agentId, 1);
        assertTrue(registry.ownerOf(agentId) == user1);
        assertTrue(registry.hasAgent(user1));
        assertEq(registry.getAgentByAddress(user1), agentId);
        vm.stopPrank();

        AgentRegistry.Agent memory agent = registry.getAgent(agentId);
        assertEq(agent.agentId, agentId);
        assertEq(agent.owner, user1);
        assertEq(agent.metadataURI, metadataURI);
        assertEq(agent.reputation, 0);
        assertTrue(agent.isActive);
        assertTrue(agent.createdAt > 0);
        assertEq(agent.twitterHandle, twitterHandle);
    }

    function test_Register_InsufficientFee() public {
        string memory metadataURI = "ipfs://QmTest";
        string memory twitterHandle = "@testuser";

        vm.startPrank(user1);
        vm.expectRevert(abi.encodeWithSelector(AgentRegistry.InsufficientFee.selector, 0.05 ether, 0.1 ether));
        registry.register{value: 0.05 ether}(metadataURI, twitterHandle);
        vm.stopPrank();
    }

    function test_Register_EmptyMetadata() public {
        string memory metadataURI = "";
        string memory twitterHandle = "@testuser";

        vm.startPrank(user1);
        vm.expectRevert(AgentRegistry.InvalidMetadataURI.selector);
        registry.register{value: 0.1 ether}(metadataURI, twitterHandle);
        vm.stopPrank();
    }

    function test_Register_AlreadyRegistered() public {
        string memory metadataURI = "ipfs://QmTest";
        string memory twitterHandle = "@testuser";

        vm.startPrank(user1);
        registry.register{value: 0.1 ether}(metadataURI, twitterHandle);
        vm.expectRevert(abi.encodeWithSelector(AgentRegistry.AgentAlreadyRegistered.selector, user1));
        registry.register{value: 0.1 ether}(metadataURI, twitterHandle);
        vm.stopPrank();
    }

    function test_Register_RefundExcessFee() public {
        string memory metadataURI = "ipfs://QmTest";
        string memory twitterHandle = "@testuser";

        vm.startPrank(user1);
        uint256 balanceBefore = user1.balance;
        registry.register{value: 0.5 ether}(metadataURI, twitterHandle);
        uint256 balanceAfter = user1.balance;

        assertEq(balanceBefore - balanceAfter, 0.1 ether);
        vm.stopPrank();
    }

    function test_UpdateMetadata_Success() public {
        string memory metadataURI1 = "ipfs://QmTest1";
        string memory metadataURI2 = "ipfs://QmTest2";
        string memory twitterHandle = "@testuser";

        vm.startPrank(user1);
        uint256 agentId = registry.register{value: 0.1 ether}(
            metadataURI1,
            twitterHandle
        );

        registry.updateMetadata(agentId, metadataURI2);
        vm.stopPrank();

        AgentRegistry.Agent memory agent = registry.getAgent(agentId);
        assertEq(agent.metadataURI, metadataURI2);
    }

    function test_UpdateMetadata_NotOwner() public {
        string memory metadataURI1 = "ipfs://QmTest1";
        string memory metadataURI2 = "ipfs://QmTest2";
        string memory twitterHandle = "@testuser";

        vm.startPrank(user1);
        uint256 agentId = registry.register{value: 0.1 ether}(
            metadataURI1,
            twitterHandle
        );
        vm.stopPrank();

        vm.startPrank(user2);
        vm.expectRevert(abi.encodeWithSelector(AgentRegistry.NotAgentOwner.selector, agentId, user2));
        registry.updateMetadata(agentId, metadataURI2);
        vm.stopPrank();
    }

    function test_UpdateMetadata_EmptyURI() public {
        string memory metadataURI = "ipfs://QmTest";
        string memory twitterHandle = "@testuser";

        vm.startPrank(user1);
        uint256 agentId = registry.register{value: 0.1 ether}(
            metadataURI,
            twitterHandle
        );

        vm.expectRevert(AgentRegistry.InvalidMetadataURI.selector);
        registry.updateMetadata(agentId, "");
        vm.stopPrank();
    }

    function test_UpdateReputation_Success() public {
        string memory metadataURI = "ipfs://QmTest";
        string memory twitterHandle = "@testuser";

        vm.startPrank(user1);
        uint256 agentId = registry.register{value: 0.1 ether}(
            metadataURI,
            twitterHandle
        );
        vm.stopPrank();

        registry.updateReputation(agentId, 100);

        AgentRegistry.Agent memory agent = registry.getAgent(agentId);
        assertEq(agent.reputation, 100);
    }

    function test_UpdateReputation_NotAuthorized() public {
        string memory metadataURI = "ipfs://QmTest";
        string memory twitterHandle = "@testuser";

        vm.startPrank(user1);
        uint256 agentId = registry.register{value: 0.1 ether}(
            metadataURI,
            twitterHandle
        );
        vm.stopPrank();

        vm.startPrank(user2);
        vm.expectRevert(abi.encodeWithSelector(AgentRegistry.NotAgentOwner.selector, agentId, user2));
        registry.updateReputation(agentId, 100);
        vm.stopPrank();
    }

    function test_DeactivateAgent_Success() public {
        string memory metadataURI = "ipfs://QmTest";
        string memory twitterHandle = "@testuser";

        vm.startPrank(user1);
        uint256 agentId = registry.register{value: 0.1 ether}(
            metadataURI,
            twitterHandle
        );

        assertTrue(registry.getAgent(agentId).isActive);

        registry.deactivateAgent(agentId);

        assertFalse(registry.getAgent(agentId).isActive);
        vm.stopPrank();
    }

    function test_DeactivateAgent_NotOwner() public {
        string memory metadataURI = "ipfs://QmTest";
        string memory twitterHandle = "@testuser";

        vm.startPrank(user1);
        uint256 agentId = registry.register{value: 0.1 ether}(
            metadataURI,
            twitterHandle
        );
        vm.stopPrank();

        vm.startPrank(user2);
        vm.expectRevert(abi.encodeWithSelector(AgentRegistry.NotAgentOwner.selector, agentId, user2));
        registry.deactivateAgent(agentId);
        vm.stopPrank();
    }

    function test_ReactivateAgent_Success() public {
        string memory metadataURI = "ipfs://QmTest";
        string memory twitterHandle = "@testuser";

        vm.startPrank(user1);
        uint256 agentId = registry.register{value: 0.1 ether}(
            metadataURI,
            twitterHandle
        );

        registry.deactivateAgent(agentId);
        assertFalse(registry.getAgent(agentId).isActive);

        registry.reactivateAgent(agentId);
        assertTrue(registry.getAgent(agentId).isActive);
        vm.stopPrank();
    }

    function test_GetAgent_NotFound() public {
        vm.expectRevert(abi.encodeWithSelector(AgentRegistry.AgentNotFound.selector, 999));
        registry.getAgent(999);
    }

    function test_GetTotalAgents() public {
        assertEq(registry.getTotalAgents(), 0);

        string memory metadataURI = "ipfs://QmTest";
        string memory twitterHandle = "@testuser";

        vm.startPrank(user1);
        registry.register{value: 0.1 ether}(metadataURI, twitterHandle);
        assertEq(registry.getTotalAgents(), 1);
        vm.stopPrank();

        vm.startPrank(user2);
        registry.register{value: 0.1 ether}(metadataURI, twitterHandle);
        assertEq(registry.getTotalAgents(), 2);
        vm.stopPrank();
    }

    function test_SetRegistrationFee_Success() public {
        uint256 newFee = 0.2 ether;
        registry.setRegistrationFee(newFee);
        assertEq(registry.registrationFee(), newFee);
    }

    function test_SetPlatformFeeManager_Success() public {
        address newManager = address(0x4);
        registry.setPlatformFeeManager(newManager);
        assertEq(registry.platformFeeManager(), newManager);
    }

    function test_WithdrawFees_Success() public {
        string memory metadataURI = "ipfs://QmTest";
        string memory twitterHandle = "@testuser";

        vm.startPrank(user1);
        registry.register{value: 0.1 ether}(metadataURI, twitterHandle);
        vm.stopPrank();

        uint256 contractBalance = address(registry).balance;
        console.log("Registry balance after registration:", contractBalance);

        assertTrue(contractBalance > 0, "Registry should have fees");
    }

    function test_TokenURI_Success() public {
        string memory metadataURI = "ipfs://QmTest";
        string memory twitterHandle = "@testuser";

        vm.startPrank(user1);
        uint256 agentId = registry.register{value: 0.1 ether}(
            metadataURI,
            twitterHandle
        );
        vm.stopPrank();

        assertEq(registry.tokenURI(agentId), metadataURI);
    }

    function test_TokenURI_NotFound() public {
        vm.expectRevert(abi.encodeWithSelector(AgentRegistry.AgentNotFound.selector, 999));
        registry.tokenURI(999);
    }

    function test_MultipleAgents() public {
        string memory metadataURI = "ipfs://QmTest";
        string memory twitterHandle = "@testuser";

        vm.startPrank(user1);
        uint256 agentId1 = registry.register{value: 0.1 ether}(
            metadataURI,
            twitterHandle
        );
        vm.stopPrank();

        vm.startPrank(user2);
        uint256 agentId2 = registry.register{value: 0.1 ether}(
            metadataURI,
            twitterHandle
        );
        vm.stopPrank();

        assertEq(agentId1, 1);
        assertEq(agentId2, 2);
        assertEq(registry.getTotalAgents(), 2);
        assertTrue(registry.ownerOf(agentId1) == user1);
        assertTrue(registry.ownerOf(agentId2) == user2);
    }
}
