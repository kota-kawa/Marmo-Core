// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

interface IPriceOracle {
    function getLatestPrice() external view returns (uint256 price, uint256 timestamp); // Returns USD cents + timestamp
    function isPriceStale() external view returns (bool);
    function getPriceUnsafe() external view returns (uint256);
}

/**
 * @title MultiSigTreasury
 * @notice Multi-signature treasury for Genesis platform campaigns
 * @dev 2-of-3 multi-sig for spends >= $300, Genesis bot as default signer
 */
contract MultiSigTreasury is ReentrancyGuard {
    /// @notice Minimum spend amount requiring multi-sig (in USD cents)
    uint256 public constant MIN_MULTISIG_SPEND = 30000; // $300.00

    /// @notice Removal fee in basis points (100-200 = 1-2%)
    uint256 public constant MIN_REMOVAL_FEE_BPS = 100; // 1%
    uint256 public constant MAX_REMOVAL_FEE_BPS = 200; // 2%

    /// @notice Basis points denominator
    uint256 public constant BPS_DENOMINATOR = 10000;

    /// @notice Number of confirmations required for execution
    uint256 public constant REQUIRED_CONFIRMATIONS = 2;

    /// @notice Maximum number of signers
    uint256 public constant MAX_SIGNERS = 3;

    /// @notice Proposal states
    enum ProposalState {
        Pending,
        Approved,
        Executed,
        Rejected,
        Expired
    }

    /// @notice Proposal types
    enum ProposalType {
        Spend,
        RemoveSigner
    }

    /// @notice Spend proposal structure
    struct SpendProposal {
        uint256 id;
        address recipient;
        uint256 amount;
        address token; // address(0) for ETH
        uint256 requiredConfirmations;
        uint256 confirmations;
        uint256 expirationTime;
        ProposalState state;
        string description;
        uint256 campaignId;
    }

    /// @notice Remove signer proposal structure
    struct RemoveSignerProposal {
        uint256 id;
        address signerToRemove;
        uint256 removalFee; // In basis points
        uint256 feeAmount;
        uint256 expirationTime;
        bool executed;
    }

    /// @notice Campaign treasury configuration
    struct TreasuryConfig {
        address[] signers;
        uint256 signerCount;
        uint256 totalFunds;
        bool isActive;
        uint256 proposalCount;
        address agentOwner;
    }

    /// @notice Campaign ID to treasury config
    mapping(uint256 => TreasuryConfig) public treasuryConfigs;

    /// @notice Campaign ID to spend proposals
    mapping(uint256 => mapping(uint256 => SpendProposal)) public spendProposals;

    /// @notice Campaign ID to remove signer proposals
    mapping(uint256 => RemoveSignerProposal) public removeSignerProposals;

    /// @notice Campaign ID => proposal ID => signer => hasConfirmed
    mapping(uint256 => mapping(uint256 => mapping(address => bool))) public confirmations;

    /// @notice Campaign ID => signer => isSigner
    mapping(uint256 => mapping(address => bool)) public isSigner;

    /// @notice Genesis bot address (platform signer)
    address public immutable genesisBot;

    /// @notice Platform fee manager address
    address public immutable feeManager;

    /// @notice Price oracle address for USD conversion
    address public priceOracle;

    /// @notice Authorized factory contract that can call on behalf of agent owners
    address public authorizedFactory;

    /// @notice Total campaigns with treasuries
    uint256 public totalTreasuries;

    /// @notice Emitted when treasury is created
    event TreasuryCreated(
        uint256 indexed campaignId,
        address indexed agentOwner,
        address genesisBot,
        address agentSigner
    );

    /// @notice Emitted when spend proposal is created
    event SpendProposalCreated(
        uint256 indexed campaignId,
        uint256 indexed proposalId,
        address recipient,
        uint256 amount,
        address token,
        string description
    );

    /// @notice Emitted when proposal is confirmed
    event ProposalConfirmed(
        uint256 indexed campaignId,
        uint256 indexed proposalId,
        address signer
    );

    /// @notice Emitted when proposal is executed
    event ProposalExecuted(
        uint256 indexed campaignId,
        uint256 indexed proposalId,
        address recipient,
        uint256 amount
    );

    /// @notice Emitted when proposal is rejected
    event ProposalRejected(
        uint256 indexed campaignId,
        uint256 indexed proposalId,
        address signer
    );

    /// @notice Emitted when signer is removed
    event SignerRemoved(
        uint256 indexed campaignId,
        address signer,
        uint256 feePaid
    );

    /// @notice Emitted when funds deposited
    event FundsDeposited(
        uint256 indexed campaignId,
        address depositor,
        uint256 amount
    );

    /// @notice Emitted when funds withdrawn
    event FundsWithdrawn(
        uint256 indexed campaignId,
        address recipient,
        uint256 amount
    );

    /// @notice Emitted when authorized factory is updated
    event AuthorizedFactoryUpdated(
        address indexed oldFactory,
        address indexed newFactory,
        address updater
    );

    /// @notice Emitted when price oracle is updated
    event PriceOracleUpdated(
        address indexed oldOracle,
        address indexed newOracle,
        address updater
    );

    /// @notice Custom errors
    error NotSigner(uint256 campaignId, address caller);
    error ProposalNotFound(uint256 campaignId, uint256 proposalId);
    error ProposalExpired(uint256 campaignId, uint256 proposalId);
    error AlreadyConfirmed(uint256 campaignId, uint256 proposalId, address signer);
    error InsufficientConfirmations(uint256 campaignId, uint256 proposalId);
    error InvalidRecipient();
    error InvalidAmount();
    error InvalidFee();
    error TreasuryNotFound(uint256 campaignId);
    error TreasuryAlreadyExists(uint256 campaignId);
    error NotAgentOwner(uint256 campaignId, address caller);
    error SignerAlreadyExists(uint256 campaignId, address signer);
    error CannotRemoveSelf();
    error InsufficientFunds(uint256 campaignId, uint256 required, uint256 available);
    error TransferFailed();
    error ProposalNotExecutable(uint256 campaignId, uint256 proposalId);
    error MaxSignersReached(uint256 campaignId);

    /**
     * @notice Constructor sets Genesis bot and fee manager addresses
     * @param _genesisBot Address of the Genesis bot signer
     * @param _feeManager Address of the platform fee manager
     */
    constructor(address _genesisBot, address _feeManager) {
        require(_genesisBot != address(0), "Invalid genesis bot address");
        require(_feeManager != address(0), "Invalid fee manager address");
        genesisBot = _genesisBot;
        feeManager = _feeManager;
    }

    /**
     * @notice Set the authorized factory contract
     * @param _factory Address of the CampaignFactory
     * @dev Only callable by genesis bot
     */
    function setAuthorizedFactory(address _factory) external {
        require(msg.sender == genesisBot, "Only genesis bot");
        require(_factory != address(0), "Invalid factory address");
        
        address oldFactory = authorizedFactory;
        authorizedFactory = _factory;
        
        emit AuthorizedFactoryUpdated(oldFactory, _factory, msg.sender);
    }

    /**
     * @notice Set the price oracle contract
     * @param _oracle Address of the price oracle
     * @dev Only callable by genesis bot
     */
    function setPriceOracle(address _oracle) external {
        require(msg.sender == genesisBot, "Only genesis bot");
        require(_oracle != address(0), "Invalid oracle address");
        
        address oldOracle = priceOracle;
        priceOracle = _oracle;
        
        emit PriceOracleUpdated(oldOracle, _oracle, msg.sender);
    }

    /// @notice Staleness threshold (4 hours - allows for some downtime)
    uint256 public constant PRICE_STALENESS_THRESHOLD = 4 hours;
    
    /// @notice Last valid price (used as fallback)
    uint256 public lastValidEthPrice = 250000; // $2500.00
    uint256 public lastValidPriceTimestamp;
    
    /**
     * @notice Get current ETH price in USD cents with staleness protection
     * @return Price in cents (e.g. 250000 = $2500.00)
     * @dev Uses oracle if fresh, otherwise uses last valid price with warning
     */
    function getEthPriceInUSD() public view returns (uint256) {
        if (priceOracle == address(0)) {
            return lastValidEthPrice;
        }
        
        try IPriceOracle(priceOracle).isPriceStale() returns (bool isStale) {
            if (!isStale) {
                try IPriceOracle(priceOracle).getLatestPrice() returns (uint256 price, uint256) {
                    if (price > 0) {
                        return price;
                    }
                } catch {}
            }
        } catch {}
        
        // Fallback to last valid price
        return lastValidEthPrice;
    }
    
    /**
     * @notice Update the last valid ETH price (called by genesis bot)
     * @param _price New price in cents
     */
    function updateLastValidEthPrice(uint256 _price) external {
        require(msg.sender == genesisBot, "Only genesis bot");
        require(_price > 0, "Invalid price");
        lastValidEthPrice = _price;
        lastValidPriceTimestamp = block.timestamp;
        emit LastValidPriceUpdated(_price, block.timestamp);
    }
    
    event LastValidPriceUpdated(uint256 price, uint256 timestamp);

    /**
     * @notice Get ETH amount for USD value
     * @param _usdCents Amount in USD cents
     * @return Amount in wei
     */
    function getEthAmountForUSD(uint256 _usdCents) external view returns (uint256) {
        uint256 ethPrice = getEthPriceInUSD();
        return (_usdCents * 1e18) / ethPrice;
    }

    /**
     * @notice Modifier to check if caller is a signer for campaign
     */
    modifier onlySigner(uint256 _campaignId) {
        if (!isSigner[_campaignId][msg.sender]) {
            revert NotSigner(_campaignId, msg.sender);
        }
        _;
    }

    /**
     * @notice Modifier to check if caller is agent owner
     */
    modifier onlyAgentOwner(uint256 _campaignId) {
        if (
            treasuryConfigs[_campaignId].agentOwner != msg.sender
            && msg.sender != authorizedFactory
        ) {
            revert NotAgentOwner(_campaignId, msg.sender);
        }
        _;
    }

    /**
     * @notice Create a new multi-sig treasury for a campaign
     * @param _campaignId The campaign ID
     * @param _agentOwner The agent owner address (proposer)
     * @param _agentSigner Additional signer address (optional, can be address(0))
     */
    function createTreasury(
        uint256 _campaignId,
        address _agentOwner,
        address _agentSigner
    ) external returns (bool) {
        if (treasuryConfigs[_campaignId].isActive) {
            revert TreasuryAlreadyExists(_campaignId);
        }

        TreasuryConfig storage config = treasuryConfigs[_campaignId];
        config.agentOwner = _agentOwner;
        config.isActive = true;

        // Always add Genesis bot as signer
        config.signers.push(genesisBot);
        isSigner[_campaignId][genesisBot] = true;
        config.signerCount = 1;

        // Add agent owner as signer
        config.signers.push(_agentOwner);
        isSigner[_campaignId][_agentOwner] = true;
        config.signerCount = 2;

        // Add optional third signer if provided
        if (_agentSigner != address(0) && _agentSigner != _agentOwner && _agentSigner != genesisBot) {
            config.signers.push(_agentSigner);
            isSigner[_campaignId][_agentSigner] = true;
            config.signerCount = 3;
        }

        totalTreasuries++;

        emit TreasuryCreated(
            _campaignId,
            _agentOwner,
            genesisBot,
            _agentSigner
        );

        return true;
    }

    /**
     * @notice Propose a spend from the treasury
     * @param _campaignId The campaign ID
     * @param _recipient The recipient address
     * @param _amount The amount to spend
     * @param _token The token address (address(0) for ETH)
     * @param _description Description of the spend
     * @return proposalId The ID of the created proposal
     */
    function proposeSpend(
        uint256 _campaignId,
        address _recipient,
        uint256 _amount,
        address _token,
        string calldata _description
    ) external onlyAgentOwner(_campaignId) returns (uint256 proposalId) {
        if (_recipient == address(0)) revert InvalidRecipient();
        if (_amount == 0) revert InvalidAmount();

        TreasuryConfig storage config = treasuryConfigs[_campaignId];
        
        // Check if sufficient funds
        if (_amount > config.totalFunds) {
            revert InsufficientFunds(_campaignId, _amount, config.totalFunds);
        }

        proposalId = config.proposalCount++;
        
        SpendProposal storage proposal = spendProposals[_campaignId][proposalId];
        proposal.id = proposalId;
        proposal.recipient = _recipient;
        proposal.amount = _amount;
        proposal.token = _token;
        proposal.requiredConfirmations = REQUIRED_CONFIRMATIONS;
        proposal.expirationTime = block.timestamp + 7 days;
        proposal.state = ProposalState.Pending;
        proposal.description = _description;
        proposal.campaignId = _campaignId;

        emit SpendProposalCreated(
            _campaignId,
            proposalId,
            _recipient,
            _amount,
            _token,
            _description
        );

        return proposalId;
    }

    /**
     * @notice Confirm a spend proposal
     * @param _campaignId The campaign ID
     * @param _proposalId The proposal ID
     */
    function confirmProposal(
        uint256 _campaignId,
        uint256 _proposalId
    ) external onlySigner(_campaignId) nonReentrant {
        SpendProposal storage proposal = spendProposals[_campaignId][_proposalId];
        
        if (proposal.id != _proposalId) {
            revert ProposalNotFound(_campaignId, _proposalId);
        }
        if (block.timestamp > proposal.expirationTime) {
            proposal.state = ProposalState.Expired;
            revert ProposalExpired(_campaignId, _proposalId);
        }
        if (proposal.state != ProposalState.Pending) {
            revert ProposalNotExecutable(_campaignId, _proposalId);
        }
        if (confirmations[_campaignId][_proposalId][msg.sender]) {
            revert AlreadyConfirmed(_campaignId, _proposalId, msg.sender);
        }

        confirmations[_campaignId][_proposalId][msg.sender] = true;
        proposal.confirmations++;

        emit ProposalConfirmed(_campaignId, _proposalId, msg.sender);

        // Auto-execute if enough confirmations
        if (proposal.confirmations >= proposal.requiredConfirmations) {
            proposal.state = ProposalState.Approved;
            _executeSpend(_campaignId, _proposalId);
        }
    }

    /**
     * @notice Reject a spend proposal
     * @param _campaignId The campaign ID
     * @param _proposalId The proposal ID
     */
    function rejectProposal(
        uint256 _campaignId,
        uint256 _proposalId
    ) external onlySigner(_campaignId) {
        SpendProposal storage proposal = spendProposals[_campaignId][_proposalId];
        
        if (proposal.id != _proposalId) {
            revert ProposalNotFound(_campaignId, _proposalId);
        }
        if (proposal.state != ProposalState.Pending) {
            revert ProposalNotExecutable(_campaignId, _proposalId);
        }

        proposal.state = ProposalState.Rejected;

        emit ProposalRejected(_campaignId, _proposalId, msg.sender);
    }

    /**
     * @notice Execute an approved spend proposal (internal)
     * @param _campaignId The campaign ID
     * @param _proposalId The proposal ID
     */
    function _executeSpend(
        uint256 _campaignId,
        uint256 _proposalId
    ) internal {
        SpendProposal storage proposal = spendProposals[_campaignId][_proposalId];
        TreasuryConfig storage config = treasuryConfigs[_campaignId];

        if (proposal.state != ProposalState.Approved) {
            revert ProposalNotExecutable(_campaignId, _proposalId);
        }
        if (proposal.confirmations < proposal.requiredConfirmations) {
            revert InsufficientConfirmations(_campaignId, _proposalId);
        }

        proposal.state = ProposalState.Executed;
        config.totalFunds -= proposal.amount;

        if (proposal.token == address(0)) {
            // Send ETH
            (bool success, ) = payable(proposal.recipient).call{value: proposal.amount}("");
            if (!success) {
                revert TransferFailed();
            }
        } else {
            // Send ERC20
            bool success = IERC20(proposal.token).transfer(proposal.recipient, proposal.amount);
            if (!success) {
                revert TransferFailed();
            }
        }

        emit ProposalExecuted(
            _campaignId,
            _proposalId,
            proposal.recipient,
            proposal.amount
        );

        emit FundsWithdrawn(
            _campaignId,
            proposal.recipient,
            proposal.amount
        );
    }

    /**
     * @notice Remove Genesis bot as signer by paying removal fee
     * @param _campaignId The campaign ID
     * @param _removalFeeBps The removal fee in basis points (100-200 = 1-2%)
     */
    function removeGenesisSigner(
        uint256 _campaignId,
        uint256 _removalFeeBps
    ) external payable onlyAgentOwner(_campaignId) nonReentrant {
        TreasuryConfig storage config = treasuryConfigs[_campaignId];
        
        if (_removalFeeBps < MIN_REMOVAL_FEE_BPS || _removalFeeBps > MAX_REMOVAL_FEE_BPS) {
            revert InvalidFee();
        }
        if (!isSigner[_campaignId][genesisBot]) {
            revert ProposalNotFound(_campaignId, 0); // Genesis not a signer
        }

        // Calculate fee based on total funds
        uint256 feeAmount = (config.totalFunds * _removalFeeBps) / BPS_DENOMINATOR;
        
        if (msg.value < feeAmount) {
            revert InvalidAmount();
        }

        // Remove Genesis from signers
        isSigner[_campaignId][genesisBot] = false;
        
        // Remove from signers array
        for (uint256 i = 0; i < config.signers.length; i++) {
            if (config.signers[i] == genesisBot) {
                config.signers[i] = config.signers[config.signers.length - 1];
                config.signers.pop();
                break;
            }
        }
        
        config.signerCount--;

        // Send fee to platform fee manager
        (bool success, ) = payable(feeManager).call{value: feeAmount}("");
        if (!success) {
            revert TransferFailed();
        }

        // Refund excess
        if (msg.value > feeAmount) {
            (success, ) = payable(msg.sender).call{value: msg.value - feeAmount}("");
            if (!success) {
                revert TransferFailed();
            }
        }

        emit SignerRemoved(_campaignId, genesisBot, feeAmount);
    }

    /**
     * @notice Deposit funds into treasury
     * @param _campaignId The campaign ID
     */
    function deposit(uint256 _campaignId) external payable {
        if (!treasuryConfigs[_campaignId].isActive) {
            revert TreasuryNotFound(_campaignId);
        }
        if (msg.value == 0) {
            revert InvalidAmount();
        }

        treasuryConfigs[_campaignId].totalFunds += msg.value;

        emit FundsDeposited(_campaignId, msg.sender, msg.value);
    }

    /**
     * @notice Get proposal details
     * @param _campaignId The campaign ID
     * @param _proposalId The proposal ID
     * @return SpendProposal struct
     */
    function getProposal(
        uint256 _campaignId,
        uint256 _proposalId
    ) external view returns (SpendProposal memory) {
        return spendProposals[_campaignId][_proposalId];
    }

    /**
     * @notice Check if signer has confirmed proposal
     * @param _campaignId The campaign ID
     * @param _proposalId The proposal ID
     * @param _signer The signer address
     * @return bool True if confirmed
     */
    function hasConfirmed(
        uint256 _campaignId,
        uint256 _proposalId,
        address _signer
    ) external view returns (bool) {
        return confirmations[_campaignId][_proposalId][_signer];
    }

    /**
     * @notice Get treasury signers
     * @param _campaignId The campaign ID
     * @return Array of signer addresses
     */
    function getSigners(uint256 _campaignId) external view returns (address[] memory) {
        return treasuryConfigs[_campaignId].signers;
    }

    /**
     * @notice Get treasury balance
     * @param _campaignId The campaign ID
     * @return uint256 Balance in wei
     */
    function getBalance(uint256 _campaignId) external view returns (uint256) {
        return treasuryConfigs[_campaignId].totalFunds;
    }

    /**
     * @notice Check if spend requires multi-sig (>= $300)
     * @param _amountWei The amount in wei
     * @return bool True if requires multi-sig
     */
    function requiresMultiSig(uint256 _amountWei) external view returns (bool) {
        // Calculate USD value of _amountWei
        // _amountWei (18 decimals) * price (cents, no decimals?) wait price is e.g. 200000 = $2000.00
        // No, price is cents per ETH. 
        // Value in cents = (_amountWei * pricePerEthCents) / 1e18
        uint256 valueInCents = (_amountWei * getEthPriceInUSD()) / 1e18;
        return valueInCents >= MIN_MULTISIG_SPEND;
    }

    /**
     * @notice Calculate removal fee for given treasury
     * @param _campaignId The campaign ID
     * @param _feeBps The fee in basis points
     * @return feeAmount The calculated fee
     */
    function calculateRemovalFee(
        uint256 _campaignId,
        uint256 _feeBps
    ) external view returns (uint256 feeAmount) {
        TreasuryConfig storage config = treasuryConfigs[_campaignId];
        feeAmount = (config.totalFunds * _feeBps) / BPS_DENOMINATOR;
        return feeAmount;
    }

    /**
     * @notice Get all pending proposals for a campaign
     * @param _campaignId The campaign ID
     * @return Array of proposal IDs
     */
    function getPendingProposals(uint256 _campaignId) external view returns (uint256[] memory) {
        TreasuryConfig storage config = treasuryConfigs[_campaignId];
        uint256[] memory pending = new uint256[](config.proposalCount);
        uint256 count = 0;
        
        for (uint256 i = 0; i < config.proposalCount; i++) {
            if (spendProposals[_campaignId][i].state == ProposalState.Pending) {
                pending[count] = i;
                count++;
            }
        }

        // Resize array
        assembly {
            mstore(pending, count)
        }
        
        return pending;
    }

    /**
     * @notice Receive ETH
     */
    receive() external payable {
        // Allow direct deposits without campaign ID
        // Funds will be assigned via deposit function
        if (msg.value > 0) {
            // This is handled through explicit deposit
            revert("Use deposit function");
        }
    }
}
