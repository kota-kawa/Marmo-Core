// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title SimplePriceOracle
 * @notice Price oracle with staleness protection for Monad Testnet
 * @dev In production, use Chainlink or similar decentralized oracle
 */
contract SimplePriceOracle {
    /// @notice Price data structure
    struct PriceData {
        uint256 price;        // Price in USD cents
        uint256 timestamp;    // Last update timestamp
        uint256 blockNumber;  // Block number of last update
    }
    
    /// @notice ETH/USD price data
    PriceData public ethPrice;
    
    /// @notice Authorized updater
    address public updater;
    
    /// @notice Maximum staleness allowed (1 hour)
    uint256 public constant MAX_STALENESS = 1 hours;
    
    /// @notice Maximum price deviation per update (20%)
    uint256 public constant MAX_DEVIATION_BPS = 2000; // 20% in basis points
    uint256 public constant BPS_DENOMINATOR = 10000;
    
    /// @notice Events
    event PriceUpdated(uint256 price, uint256 timestamp, address updater);
    event UpdaterChanged(address newUpdater);
    
    /// @notice Errors
    error StalePrice();
    error OnlyUpdater();
    error InvalidPrice();
    error ExcessiveDeviation();
    error ZeroPrice();
    
    constructor(address _updater) {
        updater = _updater;
        // Initialize with a reasonable starting price (will be updated)
        ethPrice = PriceData({
            price: 250000,  // $2500.00
            timestamp: block.timestamp,
            blockNumber: block.number
        });
    }
    
    modifier onlyUpdater() {
        if (msg.sender != updater) revert OnlyUpdater();
        _;
    }
    
    /**
     * @notice Update the ETH price
     * @param _price New price in USD cents
     */
    function updatePrice(uint256 _price) external onlyUpdater {
        if (_price == 0) revert ZeroPrice();
        
        // Check deviation from current price (only if current price > 0)
        if (ethPrice.price > 0) {
            uint256 deviation = _price > ethPrice.price 
                ? ((_price - ethPrice.price) * BPS_DENOMINATOR) / ethPrice.price
                : ((ethPrice.price - _price) * BPS_DENOMINATOR) / ethPrice.price;
            
            if (deviation > MAX_DEVIATION_BPS) {
                revert ExcessiveDeviation();
            }
        }
        
        ethPrice = PriceData({
            price: _price,
            timestamp: block.timestamp,
            blockNumber: block.number
        });
        
        emit PriceUpdated(_price, block.timestamp, msg.sender);
    }
    
    /**
     * @notice Get the latest price (reverts if stale)
     * @return price Current price in USD cents
     * @return timestamp Last update timestamp
     */
    function getLatestPrice() external view returns (uint256 price, uint256 timestamp) {
        if (block.timestamp > ethPrice.timestamp + MAX_STALENESS) {
            revert StalePrice();
        }
        return (ethPrice.price, ethPrice.timestamp);
    }
    
    /**
     * @notice Get price without staleness check (for emergency use)
     * @return price Current price in USD cents
     */
    function getPriceUnsafe() external view returns (uint256) {
        return ethPrice.price;
    }
    
    /**
     * @notice Check if price is stale
     * @return isStale True if price is stale
     */
    function isPriceStale() external view returns (bool) {
        return block.timestamp > ethPrice.timestamp + MAX_STALENESS;
    }
    
    /**
     * @notice Change the authorized updater
     * @param _newUpdater New updater address
     */
    function setUpdater(address _newUpdater) external onlyUpdater {
        updater = _newUpdater;
        emit UpdaterChanged(_newUpdater);
    }
}
