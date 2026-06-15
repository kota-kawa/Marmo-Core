// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {ERC721Enumerable} from "@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title AgentRegistry
 * @notice ERC-8004 compliant agent registry for managing AI agent identities
 * @dev Uses ERC721 for agent IDs with enumerable extension
 */
contract AgentRegistry is ERC721, ERC721Enumerable, Ownable {
    /// @notice Platform fee manager address
    address public platformFeeManager;

    /// @notice Registration fee in wei
    uint256 public registrationFee;

    /// @notice Counter for agent IDs (starts at 1)
    uint256 private _nextAgentId;

    /// @notice Agent data structure
    struct Agent {
        uint256 agentId;
        address owner;
        string metadataURI;
        uint256 reputation;
        bool isActive;
        uint256 createdAt;
        string twitterHandle; // Link to Moltbook
    }

    /// @notice Mapping from agent ID to Agent struct
    mapping(uint256 => Agent) public agents;

    /// @notice Mapping from owner address to their agent ID
    mapping(address => uint256) public agentByAddress;

    /// @notice Emitted when a new agent is registered
    event AgentRegistered(
        uint256 indexed agentId,
        address indexed owner,
        string metadataURI,
        uint256 createdAt
    );

    /// @notice Emitted when agent metadata is updated
    event MetadataUpdated(
        uint256 indexed agentId,
        string oldMetadataURI,
        string newMetadataURI
    );

    /// @notice Emitted when agent reputation is updated
    event ReputationUpdated(
        uint256 indexed agentId,
        uint256 oldReputation,
        uint256 newReputation
    );

    /// @notice Emitted when an agent is deactivated
    event AgentDeactivated(uint256 indexed agentId, address indexed owner);

    /// @notice Emitted when an agent is reactivated
    event AgentReactivated(uint256 indexed agentId, address indexed owner);

    /// @notice Emitted when registration fee is updated
    event RegistrationFeeUpdated(uint256 oldFee, uint256 newFee);

    /// @notice Emitted when platform fee manager is updated
    event PlatformFeeManagerUpdated(
        address oldManager,
        address newManager
    );

    /// @notice Thrown when agent is not found
    error AgentNotFound(uint256 agentId);

    /// @notice Thrown when agent is already registered for an address
    error AgentAlreadyRegistered(address owner);

    /// @notice Thrown when caller is not the agent owner
    error NotAgentOwner(uint256 agentId, address caller);

    /// @notice Thrown when insufficient registration fee is paid
    error InsufficientFee(uint256 paid, uint256 required);

    /// @notice Thrown when invalid metadata URI is provided
    error InvalidMetadataURI();

    /**
     * @notice Constructor initializes the registry
     * @param _registrationFee Initial registration fee in wei
     */
    constructor(uint256 _registrationFee)
        ERC721("AgentRegistry", "AGENT")
        Ownable(msg.sender)
    {
        registrationFee = _registrationFee;
        // Start agent IDs at 1
        _nextAgentId = 1;
    }

    /**
     * @notice Register a new agent
     * @param _metadataURI IPFS or other URI for agent metadata
     * @param _twitterHandle Twitter handle for Moltbook integration
     * @return agentId The ID of the newly registered agent
     */
    function register(string calldata _metadataURI, string calldata _twitterHandle)
        external
        payable
        returns (uint256 agentId)
    {
        if (bytes(_metadataURI).length == 0) {
            revert InvalidMetadataURI();
        }

        if (agentByAddress[msg.sender] != 0) {
            revert AgentAlreadyRegistered(msg.sender);
        }

        if (msg.value < registrationFee) {
            revert InsufficientFee(msg.value, registrationFee);
        }

        agentId = _nextAgentId;
        _nextAgentId++;

        Agent memory newAgent = Agent({
            agentId: agentId,
            owner: msg.sender,
            metadataURI: _metadataURI,
            reputation: 0,
            isActive: true,
            createdAt: block.timestamp,
            twitterHandle: _twitterHandle
        });

        agents[agentId] = newAgent;
        agentByAddress[msg.sender] = agentId;

        _safeMint(msg.sender, agentId);

        emit AgentRegistered(
            agentId,
            msg.sender,
            _metadataURI,
            block.timestamp
        );

        // Refund excess fee
        if (msg.value > registrationFee) {
            payable(msg.sender).transfer(msg.value - registrationFee);
        }

        return agentId;
    }

    /**
     * @notice Update agent metadata
     * @param _agentId The ID of the agent to update
     * @param _newMetadataURI New metadata URI
     */
    function updateMetadata(
        uint256 _agentId,
        string calldata _newMetadataURI
    ) external {
        if (bytes(_newMetadataURI).length == 0) {
            revert InvalidMetadataURI();
        }

        Agent storage agent = agents[_agentId];

        if (agent.agentId == 0) {
            revert AgentNotFound(_agentId);
        }

        if (agent.owner != msg.sender) {
            revert NotAgentOwner(_agentId, msg.sender);
        }

        string memory oldMetadataURI = agent.metadataURI;
        agent.metadataURI = _newMetadataURI;

        emit MetadataUpdated(_agentId, oldMetadataURI, _newMetadataURI);
    }

    /**
     * @notice Update agent reputation (only owner or fee manager)
     * @param _agentId The ID of the agent
     * @param _newReputation New reputation score
     */
    function updateReputation(
        uint256 _agentId,
        uint256 _newReputation
    ) external {
        if (msg.sender != owner() && msg.sender != platformFeeManager) {
            revert NotAgentOwner(_agentId, msg.sender);
        }

        Agent storage agent = agents[_agentId];

        if (agent.agentId == 0) {
            revert AgentNotFound(_agentId);
        }

        uint256 oldReputation = agent.reputation;
        agent.reputation = _newReputation;

        emit ReputationUpdated(_agentId, oldReputation, _newReputation);
    }

    /**
     * @notice Deactivate an agent
     * @param _agentId The ID of the agent to deactivate
     */
    function deactivateAgent(uint256 _agentId) external {
        Agent storage agent = agents[_agentId];

        if (agent.agentId == 0) {
            revert AgentNotFound(_agentId);
        }

        if (agent.owner != msg.sender) {
            revert NotAgentOwner(_agentId, msg.sender);
        }

        agent.isActive = false;

        emit AgentDeactivated(_agentId, msg.sender);
    }

    /**
     * @notice Reactivate an agent
     * @param _agentId The ID of the agent to reactivate
     */
    function reactivateAgent(uint256 _agentId) external {
        Agent storage agent = agents[_agentId];

        if (agent.agentId == 0) {
            revert AgentNotFound(_agentId);
        }

        if (agent.owner != msg.sender) {
            revert NotAgentOwner(_agentId, msg.sender);
        }

        agent.isActive = true;

        emit AgentReactivated(_agentId, msg.sender);
    }

    /**
     * @notice Get agent details by ID
     * @param _agentId The ID of the agent
     * @return Agent struct with all details
     */
    function getAgent(uint256 _agentId)
        external
        view
        returns (Agent memory)
    {
        if (agents[_agentId].agentId == 0) {
            revert AgentNotFound(_agentId);
        }
        return agents[_agentId];
    }

    /**
     * @notice Get agent by owner address
     * @param _owner The owner address
     * @return agentId The agent ID associated with the address
     */
    function getAgentByAddress(address _owner)
        external
        view
        returns (uint256 agentId)
    {
        return agentByAddress[_owner];
    }

    /**
     * @notice Check if an address has a registered agent
     * @param _owner The address to check
     * @return bool True if the address has a registered agent
     */
    function hasAgent(address _owner) external view returns (bool) {
        return agentByAddress[_owner] != 0;
    }

    /**
     * @notice Get total number of registered agents
     * @return uint256 Total count
     */
    function getTotalAgents() external view returns (uint256) {
        return _nextAgentId - 1;
    }

    /**
     * @notice Set the registration fee
     * @param _newFee New fee amount in wei
     */
    function setRegistrationFee(uint256 _newFee) external onlyOwner {
        uint256 oldFee = registrationFee;
        registrationFee = _newFee;
        emit RegistrationFeeUpdated(oldFee, _newFee);
    }

    /**
     * @notice Set the platform fee manager address
     * @param _newManager New fee manager address
     */
    function setPlatformFeeManager(address _newManager) external onlyOwner {
        address oldManager = platformFeeManager;
        platformFeeManager = _newManager;
        emit PlatformFeeManagerUpdated(oldManager, _newManager);
    }

    /**
     * @notice Withdraw collected registration fees
     * @param _recipient Address to receive the funds
     */
    function withdrawFees(address payable _recipient)
        external
        onlyOwner
    {
        uint256 balance = address(this).balance;
        require(balance > 0, "No fees to withdraw");
        (bool success, ) = _recipient.call{value: balance}("");
        require(success, "Transfer failed");
    }

    /**
     * @notice Override tokenURI to return agent metadata
     * @param tokenId The token ID
     * @return string The metadata URI
     */
    function tokenURI(uint256 tokenId)
        public
        view
        override
        returns (string memory)
    {
        if (_ownerOf(tokenId) == address(0)) {
            revert AgentNotFound(tokenId);
        }
        return agents[tokenId].metadataURI;
    }

    /**
     * @notice Override supportsInterface for ERC721Enumerable
     */
    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC721Enumerable)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }

    /**
     * @notice Override _update for Enumerable (replaces _beforeTokenTransfer in v5)
     */
    function _update(
        address to,
        uint256 tokenId,
        address auth
    ) internal override(ERC721, ERC721Enumerable) returns (address) {
        address from = super._update(to, tokenId, auth);

        // Update agent ownership mapping
        if (from != address(0) && to != address(0)) {
            Agent storage agent = agents[tokenId];
            agent.owner = to;
            delete agentByAddress[from];
            agentByAddress[to] = tokenId;
        }

        return from;
    }

    /**
     * @notice Override _increaseBalance for Enumerable
     */
    function _increaseBalance(address account, uint128 value)
        internal
        override(ERC721, ERC721Enumerable)
    {
        super._increaseBalance(account, value);
    }
}
