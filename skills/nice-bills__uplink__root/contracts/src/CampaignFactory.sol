// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import "./AgentRegistry.sol";
import "./PlatformFeeManager.sol";
import "./MultiSigTreasury.sol";

/**
 * @title CampaignFactory
 * @notice Factory contract for creating and managing fundraising campaigns
 * @dev Creates campaigns linked to registered agents with fee collection
 *      Includes ReentrancyGuard, Pausable, and Ownable for security
 */
contract CampaignFactory is ReentrancyGuard, Pausable, Ownable {
    /// @notice Reference to the agent registry
    AgentRegistry public immutable agentRegistry;

    /// @notice Reference to the platform fee manager
    PlatformFeeManager public immutable feeManager;

    /// @notice Reference to the multi-sig treasury
    address payable public immutable multiSigTreasury;

    /// @notice Platform fee in basis points (50 = 0.5%)
    uint256 public constant PLATFORM_FEE_BPS = 50;

    /// @notice Minimum spend requiring multi-sig ($300 in wei assuming $1 = 1e18 wei)


    /// @notice Basis points denominator (100% = 10000 bps)
    uint256 public constant BPS_DENOMINATOR = 10000;

    /**
     * @notice Campaign data structure
     * @param campaignId Unique identifier for the campaign
     * @param agentId ID of the agent this campaign supports
     * @param goal Fundraising goal in wei
     * @param raised Total amount raised
     * @param deadline Campaign deadline (0 for no deadline)
     * @param metadataURI IPFS URI for campaign metadata
     * @param isActive Whether the campaign is active
     * @param donors Array of donor addresses
     */
    struct Campaign {
        uint256 campaignId;
        uint256 agentId;
        uint256 goal;
        uint256 raised;      // Historical total raised (never decremented)
        uint256 withdrawn;   // Total amount withdrawn
        uint256 deadline;
        string metadataURI;
        bool isActive;
        address[] donors;
    }

    /// @notice Mapping from campaign ID to Campaign struct
    mapping(uint256 => Campaign) public campaigns;

    /// @notice Mapping from donor address to their contribution amount for each campaign
    mapping(uint256 => mapping(address => uint256)) public contributions;

    /// @notice Campaign funds balance (amount available for withdrawal by campaign owner)
    mapping(uint256 => uint256) public campaignFunds;

    /// @notice Reserved funds (locked in pending multi-sig proposals)
    mapping(uint256 => uint256) public reservedFunds;

    /// @notice Next campaign ID counter
    uint256 private _nextCampaignId = 1;

    /// @notice Tracks if an agent has an active campaign (rate limiting)
    mapping(uint256 => bool) public hasActiveCampaign;

    /// @notice Emitted when rate limiting prevents campaign creation
    event CampaignRateLimited(uint256 indexed agentId, uint256 activeCampaignId);

    /**
     * @notice Emitted when a new campaign is created
     * @param campaignId The ID of the new campaign
     * @param agentId The agent ID linked to the campaign
     * @param goal The fundraising goal
     * @param deadline The campaign deadline
     */
    event CampaignCreated(
        uint256 indexed campaignId,
        uint256 indexed agentId,
        uint256 goal,
        uint256 deadline
    );

    /**
     * @notice Emitted when a donation is received
     * @param campaignId The campaign ID
     * @param donor The donor address
     * @param amount The donation amount
     */
    event DonationReceived(
        uint256 indexed campaignId,
        address indexed donor,
        uint256 amount
    );

    /**
     * @notice Emitted when funds are withdrawn
     * @param campaignId The campaign ID
     * @param amount The amount withdrawn
     */
    event FundsWithdrawn(uint256 indexed campaignId, uint256 amount);

    /**
     * @notice Emitted when a campaign is deactivated
     * @param campaignId The campaign ID
     */
    event CampaignDeactivated(uint256 indexed campaignId);

    /// @notice Thrown when agent is not active
    error AgentNotActive(uint256 agentId);

    /// @notice Thrown when campaign does not exist
    error CampaignNotFound(uint256 campaignId);

    /// @notice Thrown when campaign is not active
    error CampaignNotActive(uint256 campaignId);

    /// @notice Thrown when campaign has expired
    error CampaignExpired(uint256 campaignId);

    /// @notice Thrown when caller is not the agent owner
    error NotAgentOwner(uint256 agentId, address caller);

    /// @notice Thrown when donation amount is zero
    error ZeroDonation();

    /// @notice Thrown when no funds to withdraw
    error NoFundsToWithdraw();

    /// @notice Thrown when multi-sig treasury not set
    error TreasuryNotSet();

    /// @notice Thrown when multi-sig spend not approved
    error MultiSigNotApproved();

    /// @notice Emitted when treasury is created for campaign
    event TreasuryCreated(
        uint256 indexed campaignId,
        address treasury,
        address agentOwner
    );

    /// @notice Emitted when spend is executed via multi-sig
    event MultiSigSpendProposed(
        uint256 indexed campaignId,
        uint256 indexed proposalId,
        address recipient,
        uint256 amount,
        address token
    );

    /**
     * @notice Constructor initializes the factory with dependencies
     * @param _agentRegistry Address of the AgentRegistry contract
     * @param _feeManager Address of the PlatformFeeManager contract
     * @param _multiSigTreasury Address of the MultiSigTreasury contract
     */
    constructor(
        address _agentRegistry,
        address _feeManager,
        address _multiSigTreasury
    ) Ownable(msg.sender) {
        require(_agentRegistry != address(0), "Invalid registry address");
        require(_feeManager != address(0), "Invalid fee manager address");
        require(_multiSigTreasury != address(0), "Invalid treasury address");
        agentRegistry = AgentRegistry(_agentRegistry);
        feeManager = PlatformFeeManager(payable(_feeManager));
        multiSigTreasury = payable(_multiSigTreasury);
    }

    /// @notice Pause all campaign operations (emergency)
    function pause() external onlyOwner {
        _pause();
    }

    /// @notice Unpause campaign operations
    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @notice Create a new fundraising campaign with multi-sig treasury
     * @param _agentId The agent ID to support
     * @param _goal Fundraising goal in wei
     * @param _duration Campaign duration in seconds (0 for no deadline)
     * @param _metadataUri IPFS URI for campaign metadata
     * @param _thirdSigner Optional third signer address (can be address(0))
     * @return campaignId The ID of the created campaign
     */
    function createCampaign(
        uint256 _agentId,
        uint256 _goal,
        uint256 _duration,
        string calldata _metadataUri,
        address _thirdSigner
    ) external whenNotPaused returns (uint256 campaignId) {
        AgentRegistry.Agent memory agent = agentRegistry.getAgent(_agentId);
        
        // ERC-8004 VERIFICATION: Agent must be registered in ERC-8004 compliant registry
        require(agent.agentId != 0, "ERC-8004: Agent not registered");
        require(agent.isActive, "ERC-8004: Agent not active");
        require(agent.owner == msg.sender, "ERC-8004: Not agent owner");
        require(_goal > 0, "Goal must be greater than 0");

        // RATE LIMITING: Check if agent already has an active campaign
        require(!hasActiveCampaign[_agentId], "You already have an active campaign");

        campaignId = _nextCampaignId++;
        uint256 deadline = _duration == 0 ? 0 : block.timestamp + _duration;

        campaigns[campaignId] = Campaign({
            campaignId: campaignId,
            agentId: _agentId,
            goal: _goal,
            raised: 0,
            withdrawn: 0,
            deadline: deadline,
            metadataURI: _metadataUri,
            isActive: true,
            donors: new address[](0)
        });

        // RATE LIMITING: Mark agent as having active campaign
        hasActiveCampaign[_agentId] = true;

        // Create multi-sig treasury for this campaign
        bool treasuryCreated = MultiSigTreasury(multiSigTreasury).createTreasury(
            campaignId,
            agent.owner,
            _thirdSigner
        );
        require(treasuryCreated, "Treasury creation failed");

        emit CampaignCreated(campaignId, _agentId, _goal, deadline);
        emit TreasuryCreated(campaignId, multiSigTreasury, agent.owner);
        
        return campaignId;
    }

    /**
     * @notice Contribute to a campaign
     * @param _campaignId The campaign ID
     */
    function contribute(uint256 _campaignId) external payable nonReentrant whenNotPaused {
        Campaign storage campaign = campaigns[_campaignId];
        require(campaign.campaignId != 0, "Campaign not found");
        require(campaign.isActive, "Campaign not active");
        require(
            block.timestamp <= campaign.deadline || campaign.deadline == 0,
            "Campaign expired"
        );
        require(msg.value > 0, "Donation must be greater than 0");

        uint256 fee = (msg.value * PLATFORM_FEE_BPS) / BPS_DENOMINATOR;
        uint256 amount = msg.value - fee;

        campaign.raised += amount;
        campaignFunds[_campaignId] += amount;

        // Track donor contribution
        if (contributions[_campaignId][msg.sender] == 0) {
            campaign.donors.push(msg.sender);
        }
        contributions[_campaignId][msg.sender] += amount;

        // Send fee to fee manager
        (bool success, ) = address(feeManager).call{value: fee}("");
        require(success, "Fee transfer failed");

        emit DonationReceived(_campaignId, msg.sender, amount);
    }

    /**
     * @notice Withdraw funds from a campaign (small amounts < $300)
     * @param _campaignId The campaign ID
     * @param _amount Amount to withdraw (must be < MIN_MULTISIG_SPEND_USD)
     */
    function withdrawFunds(uint256 _campaignId, uint256 _amount) external nonReentrant whenNotPaused {
        Campaign storage campaign = campaigns[_campaignId];
        require(campaign.campaignId != 0, "Campaign not found");
        require(_amount > 0, "Amount must be greater than 0");
        require(_amount <= campaignFunds[_campaignId], "Insufficient funds");
        require(!MultiSigTreasury(multiSigTreasury).requiresMultiSig(_amount), "Use multi-sig for large withdrawals");

        AgentRegistry.Agent memory agent = agentRegistry.getAgent(
            campaign.agentId
        );
        require(agent.owner == msg.sender, "Not agent owner");

        campaignFunds[_campaignId] -= _amount;
        campaign.withdrawn += _amount; // Track withdrawals separately (raised stays immutable)

        // Send funds to agent owner
        (bool success, ) = payable(msg.sender).call{value: _amount}("");
        require(success, "Fund transfer failed");

        emit FundsWithdrawn(_campaignId, _amount);
    }

    /**
     * @notice Propose a spend through multi-sig (for amounts >= $300)
     * @param _campaignId The campaign ID
     * @param _recipient The recipient address
     * @param _amount The amount to spend
     * @param _description Description of the spend
     * @return proposalId The ID of the created proposal
     */
    function proposeMultiSigSpend(
        uint256 _campaignId,
        address _recipient,
        uint256 _amount,
        string calldata _description
    ) external nonReentrant whenNotPaused returns (uint256 proposalId) {
        Campaign storage campaign = campaigns[_campaignId];
        require(campaign.campaignId != 0, "Campaign not found");
        require(MultiSigTreasury(multiSigTreasury).requiresMultiSig(_amount), "Use regular withdraw for small amounts");
        require(_amount <= campaignFunds[_campaignId], "Insufficient funds");

        AgentRegistry.Agent memory agent = agentRegistry.getAgent(campaign.agentId);
        require(agent.owner == msg.sender, "Not agent owner");

        // Reserve funds (tracked separately so they can be returned on rejection)
        campaignFunds[_campaignId] -= _amount;
        reservedFunds[_campaignId] += _amount;

        // Deposit reserved funds into treasury
        MultiSigTreasury(multiSigTreasury).deposit{value: _amount}(_campaignId);

        // Create proposal in multi-sig treasury
        proposalId = MultiSigTreasury(multiSigTreasury).proposeSpend(
            _campaignId,
            _recipient,
            _amount,
            address(0), // ETH
            _description
        );

        emit MultiSigSpendProposed(
            _campaignId,
            proposalId,
            _recipient,
            _amount,
            address(0)
        );

        return proposalId;
    }

    /**
     * @notice Confirm a multi-sig proposal (as Genesis bot or agent)
     * @param _campaignId The campaign ID
     * @param _proposalId The proposal ID
     */
    function confirmMultiSigProposal(
        uint256 _campaignId,
        uint256 _proposalId
    ) external {
        MultiSigTreasury(multiSigTreasury).confirmProposal(_campaignId, _proposalId);
    }

    /**
     * @notice Reject a multi-sig proposal
     * @param _campaignId The campaign ID
     * @param _proposalId The proposal ID
     */
    function rejectMultiSigProposal(
        uint256 _campaignId,
        uint256 _proposalId
    ) external {
        // Get proposal amount before rejecting
        MultiSigTreasury.SpendProposal memory proposal = MultiSigTreasury(multiSigTreasury).getProposal(_campaignId, _proposalId);
        
        MultiSigTreasury(multiSigTreasury).rejectProposal(_campaignId, _proposalId);
        
        // Return reserved funds back to available campaign funds
        if (proposal.amount > 0 && reservedFunds[_campaignId] >= proposal.amount) {
            reservedFunds[_campaignId] -= proposal.amount;
            campaignFunds[_campaignId] += proposal.amount;
        }
    }

    /**
     * @notice Remove Genesis bot as signer (pay 1-2% fee)
     * @param _campaignId The campaign ID
     * @param _removalFeeBps Removal fee in basis points (100-200)
     */
    function removeGenesisSigner(
        uint256 _campaignId,
        uint256 _removalFeeBps
    ) external payable {
        Campaign storage campaign = campaigns[_campaignId];
        require(campaign.campaignId != 0, "Campaign not found");

        AgentRegistry.Agent memory agent = agentRegistry.getAgent(campaign.agentId);
        require(agent.owner == msg.sender, "Not agent owner");

        MultiSigTreasury(multiSigTreasury).removeGenesisSigner{value: msg.value}(
            _campaignId,
            _removalFeeBps
        );
    }

    /**
     * @notice Deposit funds directly to multi-sig treasury
     * @param _campaignId The campaign ID
     */
    function depositToTreasury(uint256 _campaignId) external payable {
        require(campaigns[_campaignId].campaignId != 0, "Campaign not found");
        require(msg.value > 0, "Amount must be greater than 0");

        MultiSigTreasury(multiSigTreasury).deposit{value: msg.value}(_campaignId);
    }

    /**
     * @notice Get treasury balance for a campaign
     * @param _campaignId The campaign ID
     * @return balance The treasury balance
     */
    function getTreasuryBalance(uint256 _campaignId) external view returns (uint256) {
        return MultiSigTreasury(multiSigTreasury).getBalance(_campaignId);
    }

    /**
     * @notice Get treasury signers for a campaign
     * @param _campaignId The campaign ID
     * @return signers Array of signer addresses
     */
    function getTreasurySigners(uint256 _campaignId) external view returns (address[] memory) {
        return MultiSigTreasury(multiSigTreasury).getSigners(_campaignId);
    }

    /**
     * @notice Deactivate a campaign
     * @param _campaignId The campaign ID
     */
    function deactivateCampaign(uint256 _campaignId) external {
        Campaign storage campaign = campaigns[_campaignId];
        require(campaign.campaignId != 0, "Campaign not found");
        require(campaign.isActive, "Campaign already inactive");

        AgentRegistry.Agent memory agent = agentRegistry.getAgent(
            campaign.agentId
        );
        require(agent.owner == msg.sender, "Not agent owner");

        campaign.isActive = false;
        emit CampaignDeactivated(_campaignId);
    }

    /**
     * @notice Get campaign details
     * @param _campaignId The campaign ID
     * @return Campaign struct with all details
     */
    function getCampaign(uint256 _campaignId)
        external
        view
        returns (Campaign memory)
    {
        require(campaigns[_campaignId].campaignId != 0, "Campaign not found");
        return campaigns[_campaignId];
    }

    /**
     * @notice Get campaign donors
     * @param _campaignId The campaign ID
     * @return donors Array of donor addresses
     */
    function getCampaignDonors(uint256 _campaignId)
        external
        view
        returns (address[] memory donors)
    {
        require(campaigns[_campaignId].campaignId != 0, "Campaign not found");
        return campaigns[_campaignId].donors;
    }

    /**
     * @notice Get donor's contribution amount
     * @param _campaignId The campaign ID
     * @param _donor The donor address
     * @return amount The contribution amount
     */
    function getDonorContribution(
        uint256 _campaignId,
        address _donor
    ) external view returns (uint256) {
        return contributions[_campaignId][_donor];
    }

    /**
     * @notice Get total number of campaigns
     * @return uint256 Total count
     */
    function getTotalCampaigns() external view returns (uint256) {
        return _nextCampaignId - 1;
    }

    /**
     * @notice Complete a campaign and release rate limit
     * @param _campaignId The campaign ID to complete
     */
    function completeCampaign(uint256 _campaignId) external {
        Campaign storage campaign = campaigns[_campaignId];
        require(campaign.campaignId != 0, "Campaign not found");
        
        AgentRegistry.Agent memory agent = agentRegistry.getAgent(campaign.agentId);
        require(agent.owner == msg.sender, "Not campaign owner");
        require(campaign.isActive, "Campaign not active");
        
        // Mark campaign as inactive
        campaign.isActive = false;
        
        // RATE LIMITING: Release the rate limit
        hasActiveCampaign[campaign.agentId] = false;
        
        emit CampaignCompleted(_campaignId, campaign.agentId);
    }

    /**
     * @notice Cancel a campaign and release rate limit
     * @param _campaignId The campaign ID to cancel
     */
    function cancelCampaign(uint256 _campaignId) external {
        Campaign storage campaign = campaigns[_campaignId];
        require(campaign.campaignId != 0, "Campaign not found");
        
        AgentRegistry.Agent memory agent = agentRegistry.getAgent(campaign.agentId);
        require(agent.owner == msg.sender, "Not campaign owner");
        require(campaign.isActive, "Campaign not active");
        require(campaign.raised == 0, "Cannot cancel campaign with funds");
        
        // Mark campaign as inactive
        campaign.isActive = false;
        
        // RATE LIMITING: Release the rate limit
        hasActiveCampaign[campaign.agentId] = false;
        
        emit CampaignCancelled(_campaignId, campaign.agentId);
    }

    // Events for completion/cancellation
    event CampaignCompleted(uint256 indexed campaignId, uint256 indexed agentId);
    event CampaignCancelled(uint256 indexed campaignId, uint256 indexed agentId);
}
