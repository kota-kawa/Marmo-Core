// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/SimplePriceOracle.sol";
import "../src/MultiSigTreasury.sol";
import "../src/PlatformFeeManager.sol";

/**
 * @title DeploySecurityFixesOnly
 * @notice Deploys only the contracts with security fixes
 * @dev Uses existing PlatformFeeManager and updates treasury
 */
contract DeploySecurityFixesOnly is Script {
    /// @notice Existing contract addresses (keep these)
    address public constant EXISTING_FEE_MANAGER = 0x3D5ec733ED7970B1f148Ee0dFAAf0cFee985a990;
    address public constant EXISTING_FACTORY = 0xEd4eb043c9faAd76B1Ec5a4522495813099FF77A;
    
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployerAddress = vm.addr(deployerPrivateKey);
        
        vm.startBroadcast(deployerPrivateKey);

        console.log("=== Deploying Security Fixes Only ===");
        console.log("Deployer:", deployerAddress);
        console.log("");

        // 1. Deploy SimplePriceOracle
        SimplePriceOracle priceOracle = new SimplePriceOracle(deployerAddress);
        console.log("SimplePriceOracle:", address(priceOracle));
        
        // Set initial price
        priceOracle.updatePrice(250000); // $2500.00
        console.log("Initial price: $2500.00");

        // 2. Deploy MultiSigTreasury (with security fixes)
        MultiSigTreasury multiSigTreasury = new MultiSigTreasury(
            deployerAddress,
            EXISTING_FEE_MANAGER
        );
        console.log("MultiSigTreasury (NEW):", address(multiSigTreasury));
        
        // Connect price oracle
        multiSigTreasury.setPriceOracle(address(priceOracle));
        console.log("Price oracle connected");
        
        // Authorize existing factory
        multiSigTreasury.setAuthorizedFactory(EXISTING_FACTORY);
        console.log("Factory authorized");

        console.log("");
        console.log("=== Deployment Complete ===");
        console.log("NEW MultiSigTreasury:", address(multiSigTreasury));
        console.log("NEW PriceOracle:", address(priceOracle));
        console.log("===========================");

        vm.stopBroadcast();
    }
}
