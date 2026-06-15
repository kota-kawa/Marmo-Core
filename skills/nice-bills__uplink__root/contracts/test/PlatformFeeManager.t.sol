// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/PlatformFeeManager.sol";

/**
 * @title PlatformFeeManagerTest
 * @notice Comprehensive test suite for PlatformFeeManager contract
 * @dev Tests fee calculation, collection, withdrawal, and configuration
 */
contract PlatformFeeManagerTest is Test {
    PlatformFeeManager public feeManager;
    address public owner;
    address public feeRecipient;
    address public user1;
    address public user2;

    event FeeCollected(address indexed from, uint256 amount, uint256 fee);
    event FeesWithdrawn(address indexed recipient, uint256 amount);
    event FeeRecipientUpdated(
        address indexed oldRecipient,
        address indexed newRecipient
    );

    function setUp() public {
        owner = address(this);
        feeRecipient = address(0x1);
        user1 = address(0x2);
        user2 = address(0x3);

        vm.deal(user1, 10 ether);
        vm.deal(user2, 10 ether);

        feeManager = new PlatformFeeManager(feeRecipient);
    }

    function test_Constructor_Success() public {
        assertEq(feeManager.feeRecipient(), feeRecipient);
        assertEq(feeManager.totalFeesCollected(), 0);
        assertEq(feeManager.availableFees(), 0);
    }

    function test_Constructor_ZeroRecipient() public {
        vm.expectRevert(PlatformFeeManager.InvalidFeeRecipient.selector);
        feeManager = new PlatformFeeManager(address(0));
    }

    function test_CalculateFee_Success() public {
        uint256 amount = 1 ether;
        (uint256 fee, uint256 netAmount) = feeManager.calculateFee(amount);

        uint256 expectedFee = (1 ether * 50) / 10000;
        uint256 expectedNet = 1 ether - expectedFee;

        assertEq(fee, expectedFee);
        assertEq(netAmount, expectedNet);
    }

    function test_CalculateFee_ZeroAmount() public {
        vm.expectRevert(PlatformFeeManager.ZeroAmount.selector);
        feeManager.calculateFee(0);
    }

    function test_CollectFee_Success() public {
        uint256 amount = 1 ether;

        vm.startPrank(user1);
        (uint256 fee, uint256 netAmount) = feeManager.collectFee(amount);
        vm.stopPrank();

        uint256 expectedFee = (1 ether * 50) / 10000;
        uint256 expectedNet = 1 ether - expectedFee;

        assertEq(fee, expectedFee);
        assertEq(netAmount, expectedNet);
        assertEq(feeManager.totalFeesCollected(), expectedFee);
        assertEq(feeManager.availableFees(), expectedFee);
    }

    function test_CollectFee_MultipleTimes() public {
        uint256 amount1 = 1 ether;
        uint256 amount2 = 0.5 ether;

        vm.startPrank(user1);
        feeManager.collectFee(amount1);
        feeManager.collectFee(amount2);
        vm.stopPrank();

        uint256 expectedFee1 = (1 ether * 50) / 10000;
        uint256 expectedFee2 = (0.5 ether * 50) / 10000;

        assertEq(
            feeManager.totalFeesCollected(),
            expectedFee1 + expectedFee2
        );
        assertEq(
            feeManager.availableFees(),
            expectedFee1 + expectedFee2
        );
    }

    function test_CollectFee_ZeroAmount() public {
        vm.startPrank(user1);
        vm.expectRevert(PlatformFeeManager.ZeroAmount.selector);
        feeManager.collectFee(0);
        vm.stopPrank();
    }

    function test_WithdrawFees_Success() public {
        uint256 amount = 1 ether;
        uint256 balanceBefore = feeRecipient.balance;

        vm.startPrank(user1);
        feeManager.collectFee(amount);
        vm.stopPrank();

        vm.startPrank(feeRecipient);
        feeManager.withdrawFees();
        vm.stopPrank();

        uint256 expectedFee = (1 ether * 50) / 10000;
        assertEq(feeRecipient.balance - balanceBefore, expectedFee);
        assertEq(feeManager.availableFees(), 0);
        assertEq(feeManager.totalFeesCollected(), expectedFee);
    }

    function test_WithdrawFees_Owner() public {
        uint256 amount = 1 ether;
        uint256 balanceBefore = feeRecipient.balance;

        vm.startPrank(user1);
        feeManager.collectFee(amount);
        vm.stopPrank();

        feeManager.withdrawFees();

        uint256 expectedFee = (1 ether * 50) / 10000;
        assertEq(feeRecipient.balance - balanceBefore, expectedFee);
        assertEq(feeManager.availableFees(), 0);
    }

    function test_WithdrawFees_Unauthorized() public {
        uint256 amount = 1 ether;

        vm.startPrank(user1);
        feeManager.collectFee(amount);
        vm.stopPrank();

        vm.startPrank(user2);
        vm.expectRevert("Not authorized");
        feeManager.withdrawFees();
        vm.stopPrank();
    }

    function test_WithdrawFees_NoFees() public {
        vm.startPrank(feeRecipient);
        vm.expectRevert(PlatformFeeManager.NoFeesAvailable.selector);
        feeManager.withdrawFees();
        vm.stopPrank();
    }

    function test_WithdrawFees_MultipleWithdrawals() public {
        uint256 amount = 1 ether;
        uint256 balanceBefore = feeRecipient.balance;

        vm.startPrank(user1);
        feeManager.collectFee(amount);
        feeManager.collectFee(amount);
        vm.stopPrank();

        vm.startPrank(feeRecipient);
        feeManager.withdrawFees();
        vm.stopPrank();

        uint256 expectedFee = (1 ether * 50) / 10000;
        assertEq(feeRecipient.balance - balanceBefore, expectedFee * 2);
        assertEq(feeManager.availableFees(), 0);
    }

    function test_SetFeeRecipient_Success() public {
        address newRecipient = address(0x4);

        feeManager.setFeeRecipient(newRecipient);
        assertEq(feeManager.feeRecipient(), newRecipient);
    }

    function test_SetFeeRecipient_ZeroAddress() public {
        vm.expectRevert(PlatformFeeManager.InvalidFeeRecipient.selector);
        feeManager.setFeeRecipient(address(0));
    }

    function test_SetFeeRecipient_NotOwner() public {
        address newRecipient = address(0x4);

        vm.startPrank(user1);
        vm.expectRevert();
        feeManager.setFeeRecipient(newRecipient);
        vm.stopPrank();
    }

    function test_GetFeeConfig() public {
        (
            uint256 feeBps,
            uint256 denominator,
            address recipient
        ) = feeManager.getFeeConfig();

        assertEq(feeBps, 50);
        assertEq(denominator, 10000);
        assertEq(recipient, feeRecipient);
    }

    function test_Receive_Success() public {
        uint256 amount = 1 ether;
        uint256 balanceBefore = address(feeManager).balance;

        vm.startPrank(user1);
        payable(address(feeManager)).transfer(amount);
        vm.stopPrank();

        assertEq(address(feeManager).balance - balanceBefore, amount);
        assertEq(feeManager.totalFeesCollected(), amount);
        assertEq(feeManager.availableFees(), amount);
    }

    function test_EmergencyWithdraw_Success() public {
        uint256 amount = 1 ether;
        address recipient = address(0x4);
        uint256 balanceBefore = recipient.balance;

        vm.startPrank(user1);
        payable(address(feeManager)).transfer(amount);
        vm.stopPrank();

        feeManager.emergencyWithdraw(payable(recipient));

        assertEq(recipient.balance - balanceBefore, amount);
        assertEq(feeManager.availableFees(), 0);
    }

    function test_EmergencyWithdraw_NotOwner() public {
        uint256 amount = 1 ether;
        address recipient = address(0x4);

        vm.startPrank(user1);
        payable(address(feeManager)).transfer(amount);
        vm.stopPrank();

        vm.startPrank(user2);
        vm.expectRevert();
        feeManager.emergencyWithdraw(payable(recipient));
        vm.stopPrank();
    }

    function test_EmergencyWithdraw_NoFees() public {
        address recipient = address(0x4);

        vm.expectRevert(PlatformFeeManager.NoFeesAvailable.selector);
        feeManager.emergencyWithdraw(payable(recipient));
    }

    function test_GetBalance() public {
        uint256 amount = 1 ether;

        console.log("User1 balance before:", user1.balance);
        console.log("FeeManager balance before:", address(feeManager).balance);

        vm.startPrank(user1);
        payable(address(feeManager)).transfer(amount);
        vm.stopPrank();

        console.log("User1 balance after:", user1.balance);
        console.log("FeeManager balance after:", address(feeManager).balance);

        assertEq(address(feeManager).balance, amount);
    }

    function test_FeeCalculations() public {
        uint256 amount1 = 1 ether;
        uint256 amount2 = 100 ether;
        uint256 amount3 = 0.001 ether;

        (uint256 fee1, uint256 netAmount1) = feeManager.calculateFee(amount1);
        (uint256 fee2, uint256 netAmount2) = feeManager.calculateFee(amount2);
        (uint256 fee3, uint256 netAmount3) = feeManager.calculateFee(amount3);

        uint256 expectedFee1 = (1 ether * 50) / 10000;
        uint256 expectedFee2 = (100 ether * 50) / 10000;
        uint256 expectedFee3 = (0.001 ether * 50) / 10000;

        assertEq(fee1, expectedFee1);
        assertEq(netAmount1, amount1 - expectedFee1);

        assertEq(fee2, expectedFee2);
        assertEq(netAmount2, amount2 - expectedFee2);

        assertEq(fee3, expectedFee3);
        assertEq(netAmount3, amount3 - expectedFee3);
    }

    function test_MultipleUsersCollectFees() public {
        uint256 amount = 1 ether;

        vm.startPrank(user1);
        feeManager.collectFee(amount);
        vm.stopPrank();

        vm.startPrank(user2);
        feeManager.collectFee(amount);
        vm.stopPrank();

        uint256 expectedFee = (1 ether * 50) / 10000;
        assertEq(feeManager.totalFeesCollected(), expectedFee * 2);
        assertEq(feeManager.availableFees(), expectedFee * 2);
    }

    function test_PartialWithdrawal() public {
        uint256 amount1 = 1 ether;
        uint256 amount2 = 1 ether;
        uint256 balanceBefore = feeRecipient.balance;

        vm.startPrank(user1);
        feeManager.collectFee(amount1);
        vm.stopPrank();

        vm.startPrank(user1);
        feeManager.collectFee(amount2);
        vm.stopPrank();

        vm.startPrank(feeRecipient);
        feeManager.withdrawFees();
        vm.stopPrank();

        uint256 expectedFee = (1 ether * 50) / 10000;
        assertEq(feeRecipient.balance - balanceBefore, expectedFee * 2);
        assertEq(feeManager.availableFees(), 0);
    }
}
