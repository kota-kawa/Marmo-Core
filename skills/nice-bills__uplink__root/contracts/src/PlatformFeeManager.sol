// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title PlatformFeeManager
 * @notice Manages platform fees for the fundraising platform
 * @dev Calculates and collects fees on contributions
 */
contract PlatformFeeManager is Ownable, ReentrancyGuard {
    /// @notice Platform fee in basis points (50 = 0.5%)
    uint256 public constant PLATFORM_FEE_BPS = 50;

    /// @notice Basis points denominator (100% = 10000 bps)
    uint256 public constant BPS_DENOMINATOR = 10000;

    /// @notice Fee recipient address
    address public feeRecipient;

    /// @notice Total fees collected
    uint256 public totalFeesCollected;

    /// @notice Fees available for withdrawal
    uint256 public availableFees;

    /// @notice Emitted when fee is calculated
    event FeeCalculated(
        uint256 amount,
        uint256 fee,
        uint256 netAmount
    );

    /// @notice Emitted when fee is collected
    event FeeCollected(
        address indexed from,
        uint256 amount,
        uint256 fee
    );

    /// @notice Emitted when fees are withdrawn
    event FeesWithdrawn(
        address indexed recipient,
        uint256 amount
    );

    /// @notice Emitted when fee recipient is updated
    event FeeRecipientUpdated(
        address oldRecipient,
        address newRecipient
    );

    /// @notice Thrown when fee recipient is zero address
    error InvalidFeeRecipient();

    /// @notice Thrown when amount is zero
    error ZeroAmount();

    /// @notice Thrown when no fees available to withdraw
    error NoFeesAvailable();

    /// @notice Thrown when transfer fails
    error TransferFailed();

    /**
     * @notice Constructor sets initial fee recipient
     * @param _feeRecipient Address to receive platform fees
     */
    constructor(address _feeRecipient) Ownable(msg.sender) {
        if (_feeRecipient == address(0)) {
            revert InvalidFeeRecipient();
        }
        feeRecipient = _feeRecipient;
    }

    /**
     * @notice Calculate platform fee for a given amount
     * @param _amount The contribution amount
     * @return fee The platform fee
     * @return netAmount The amount minus fee
     */
    function calculateFee(uint256 _amount)
        external
        pure
        returns (uint256 fee, uint256 netAmount)
    {
        if (_amount == 0) {
            revert ZeroAmount();
        }

        fee = (_amount * PLATFORM_FEE_BPS) / BPS_DENOMINATOR;
        netAmount = _amount - fee;

        return (fee, netAmount);
    }

    /**
     * @notice Collect platform fee from a contribution
     * @param _amount The contribution amount
     * @return fee The fee collected
     * @return netAmount The net amount after fee
     */
    function collectFee(uint256 _amount)
        external
        returns (uint256 fee, uint256 netAmount)
    {
        if (_amount == 0) {
            revert ZeroAmount();
        }

        fee = (_amount * PLATFORM_FEE_BPS) / BPS_DENOMINATOR;
        netAmount = _amount - fee;

        totalFeesCollected += fee;
        availableFees += fee;

        emit FeeCollected(msg.sender, _amount, fee);
        emit FeeCalculated(_amount, fee, netAmount);

        return (fee, netAmount);
    }

    /**
     * @notice Withdraw accumulated fees to fee recipient
     */
    function withdrawFees()
        external
        nonReentrant
    {
        if (availableFees == 0) {
            revert NoFeesAvailable();
        }

        uint256 amount = availableFees;
        availableFees = 0;

        (bool success, ) = payable(feeRecipient).call{value: amount}("");
        if (!success) {
            revert TransferFailed();
        }

        emit FeesWithdrawn(feeRecipient, amount);
    }

    /**
     * @notice Set new fee recipient
     * @param _newRecipient New recipient address
     */
    function setFeeRecipient(address _newRecipient)
        external
        onlyOwner
    {
        if (_newRecipient == address(0)) {
            revert InvalidFeeRecipient();
        }

        address oldRecipient = feeRecipient;
        feeRecipient = _newRecipient;

        emit FeeRecipientUpdated(oldRecipient, _newRecipient);
    }

    /**
     * @notice Get current fee configuration
     * @return feeBps Fee in basis points
     * @return denominator Basis points denominator
     * @return recipient Current fee recipient
     */
    function getFeeConfig()
        external
        view
        returns (
            uint256 feeBps,
            uint256 denominator,
            address recipient
        )
    {
        return (PLATFORM_FEE_BPS, BPS_DENOMINATOR, feeRecipient);
    }

    /**
     * @notice Receive ETH for fee collection
     */
    receive() external payable {
        availableFees += msg.value;
        totalFeesCollected += msg.value;
        emit FeeCollected(msg.sender, msg.value, msg.value);
    }

    /**
     * @notice Emergency withdraw all ETH (only owner)
     * @param _recipient Address to receive funds
     */
    function emergencyWithdraw(address payable _recipient)
        external
        onlyOwner
        nonReentrant
    {
        uint256 balance = address(this).balance;
        if (balance == 0) {
            revert NoFeesAvailable();
        }

        availableFees = 0;

        (bool success, ) = _recipient.call{value: balance}("");
        if (!success) {
            revert TransferFailed();
        }

        emit FeesWithdrawn(_recipient, balance);
    }
}
