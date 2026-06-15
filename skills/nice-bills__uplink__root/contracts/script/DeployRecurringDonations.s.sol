// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/RecurringDonations.sol";

/**
 * @title DeployRecurringDonations
 * @notice Deployment script for the RecurringDonations contract
 * @dev Uses the already-deployed CampaignFactory address from DEPLOYMENT.md
 *
 * Usage:
 *   forge script script/DeployRecurringDonations.s.sol:DeployRecurringDonations \
 *     --rpc-url $MONAD_RPC_URL \
 *     --broadcast \
 *     --verify
 */
contract DeployRecurringDonations is Script {
    /// @notice Already-deployed CampaignFactory on Monad Testnet
    address public constant CAMPAIGN_FACTORY = 0xbEC03ac2Fda75cbb5c7f0c510d75F5d48C68AfE0;

    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        console.log("Deployer:", deployer);
        console.log("Deployer balance:", deployer.balance);
        console.log("CampaignFactory:", CAMPAIGN_FACTORY);

        vm.startBroadcast(deployerPrivateKey);

        RecurringDonations recurring = new RecurringDonations(CAMPAIGN_FACTORY);
        console.log("RecurringDonations deployed at:", address(recurring));

        vm.stopBroadcast();

        console.log("\n=== RecurringDonations Deployment ===");
        console.log("Contract:", address(recurring));
        console.log("CampaignFactory:", CAMPAIGN_FACTORY);
        console.log("====================================\n");
    }
}
