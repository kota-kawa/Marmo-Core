// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "./CampaignFactory.sol";

/**
 * @title RecurringDonations
 * @notice Manages recurring donation subscriptions to campaigns
 * @dev Donors pre-fund a balance, then a keeper (or anyone) can trigger
 *      periodic donations based on the subscription schedule.
 *      Works with the existing CampaignFactory for contributions.
 */
contract RecurringDonations {
    // ============ State ============

    /// @notice CampaignFactory reference
    CampaignFactory public immutable campaignFactory;

    /// @notice Subscription data
    struct Subscription {
        address donor;
        uint256 campaignId;
        uint256 amount;         // Per-period donation amount
        uint256 interval;       // Seconds between donations (e.g. 7 days = 604800)
        uint256 nextExecution;  // Timestamp of next scheduled donation
        uint256 totalExecuted;  // Number of donations made so far
        uint256 maxExecutions;  // 0 = unlimited
        bool active;
    }

    /// @notice All subscriptions
    mapping(uint256 => Subscription) public subscriptions;
    uint256 public nextSubscriptionId;

    /// @notice Donor balances (pre-funded)
    mapping(address => uint256) public balances;

    /// @notice Donor -> list of subscription IDs
    mapping(address => uint256[]) public donorSubscriptions;

    // ============ Events ============

    event SubscriptionCreated(
        uint256 indexed subscriptionId,
        address indexed donor,
        uint256 indexed campaignId,
        uint256 amount,
        uint256 interval,
        uint256 maxExecutions
    );

    event SubscriptionExecuted(
        uint256 indexed subscriptionId,
        uint256 indexed campaignId,
        uint256 amount,
        uint256 executionNumber
    );

    event SubscriptionCancelled(uint256 indexed subscriptionId, address indexed donor);
    event BalanceDeposited(address indexed donor, uint256 amount);
    event BalanceWithdrawn(address indexed donor, uint256 amount);

    // ============ Errors ============

    error InsufficientBalance(uint256 available, uint256 required);
    error SubscriptionNotActive(uint256 subscriptionId);
    error NotSubscriptionOwner(uint256 subscriptionId);
    error TooEarlyToExecute(uint256 nextExecution, uint256 currentTime);
    error InvalidInterval();
    error InvalidAmount();
    error MaxExecutionsReached(uint256 subscriptionId);

    // ============ Constructor ============

    constructor(address _campaignFactory) {
        campaignFactory = CampaignFactory(_campaignFactory);
        nextSubscriptionId = 1;
    }

    // ============ Donor Balance Management ============

    /// @notice Deposit funds to cover future recurring donations
    function deposit() external payable {
        require(msg.value > 0, "Must deposit > 0");
        balances[msg.sender] += msg.value;
        emit BalanceDeposited(msg.sender, msg.value);
    }

    /// @notice Withdraw unused balance
    function withdraw(uint256 _amount) external {
        if (balances[msg.sender] < _amount) {
            revert InsufficientBalance(balances[msg.sender], _amount);
        }
        balances[msg.sender] -= _amount;
        (bool success,) = payable(msg.sender).call{value: _amount}("");
        require(success, "Transfer failed");
        emit BalanceWithdrawn(msg.sender, _amount);
    }

    // ============ Subscription Management ============

    /**
     * @notice Create a recurring donation subscription
     * @param _campaignId Campaign to donate to
     * @param _amount Amount per donation (in wei)
     * @param _interval Seconds between donations (min 1 hour)
     * @param _maxExecutions Max number of donations (0 = unlimited)
     */
    function createSubscription(
        uint256 _campaignId,
        uint256 _amount,
        uint256 _interval,
        uint256 _maxExecutions
    ) external returns (uint256 subscriptionId) {
        if (_amount == 0) revert InvalidAmount();
        if (_interval < 1 hours) revert InvalidInterval();

        // Verify campaign exists via factory
        (uint256 cId,,,,,,,) = campaignFactory.campaigns(_campaignId);
        require(cId != 0, "Campaign not found");

        subscriptionId = nextSubscriptionId++;

        subscriptions[subscriptionId] = Subscription({
            donor: msg.sender,
            campaignId: _campaignId,
            amount: _amount,
            interval: _interval,
            nextExecution: block.timestamp, // First execution can happen immediately
            totalExecuted: 0,
            maxExecutions: _maxExecutions,
            active: true
        });

        donorSubscriptions[msg.sender].push(subscriptionId);

        emit SubscriptionCreated(
            subscriptionId,
            msg.sender,
            _campaignId,
            _amount,
            _interval,
            _maxExecutions
        );
    }

    /**
     * @notice Execute a pending subscription donation
     * @dev Can be called by anyone (keeper pattern). Donor's pre-funded balance is used.
     * @param _subscriptionId The subscription to execute
     */
    function execute(uint256 _subscriptionId) external {
        Subscription storage sub = subscriptions[_subscriptionId];

        if (!sub.active) revert SubscriptionNotActive(_subscriptionId);
        if (block.timestamp < sub.nextExecution) {
            revert TooEarlyToExecute(sub.nextExecution, block.timestamp);
        }
        if (sub.maxExecutions != 0 && sub.totalExecuted >= sub.maxExecutions) {
            revert MaxExecutionsReached(_subscriptionId);
        }
        if (balances[sub.donor] < sub.amount) {
            // Auto-pause if donor runs out of funds
            sub.active = false;
            emit SubscriptionCancelled(_subscriptionId, sub.donor);
            revert InsufficientBalance(balances[sub.donor], sub.amount);
        }

        // Deduct from donor balance
        balances[sub.donor] -= sub.amount;

        // Send to CampaignFactory
        campaignFactory.contribute{value: sub.amount}(sub.campaignId);

        // Update subscription state
        sub.totalExecuted++;
        sub.nextExecution = block.timestamp + sub.interval;

        // Auto-deactivate if max reached
        if (sub.maxExecutions != 0 && sub.totalExecuted >= sub.maxExecutions) {
            sub.active = false;
        }

        emit SubscriptionExecuted(
            _subscriptionId,
            sub.campaignId,
            sub.amount,
            sub.totalExecuted
        );
    }

    /**
     * @notice Cancel a subscription
     * @param _subscriptionId The subscription to cancel
     */
    function cancel(uint256 _subscriptionId) external {
        Subscription storage sub = subscriptions[_subscriptionId];
        if (sub.donor != msg.sender) revert NotSubscriptionOwner(_subscriptionId);
        if (!sub.active) revert SubscriptionNotActive(_subscriptionId);

        sub.active = false;
        emit SubscriptionCancelled(_subscriptionId, msg.sender);
    }

    // ============ View Functions ============

    /// @notice Get all subscription IDs for a donor
    function getDonorSubscriptions(address _donor) external view returns (uint256[] memory) {
        return donorSubscriptions[_donor];
    }

    /// @notice Check if a subscription is ready to execute
    function isExecutable(uint256 _subscriptionId) external view returns (bool) {
        Subscription storage sub = subscriptions[_subscriptionId];
        return sub.active
            && block.timestamp >= sub.nextExecution
            && balances[sub.donor] >= sub.amount
            && (sub.maxExecutions == 0 || sub.totalExecuted < sub.maxExecutions);
    }

    /// @notice Get multiple subscriptions that are ready to execute (for keepers)
    function getExecutableSubscriptions(uint256 _from, uint256 _to)
        external
        view
        returns (uint256[] memory)
    {
        if (_to > nextSubscriptionId) _to = nextSubscriptionId;
        uint256[] memory temp = new uint256[](_to - _from);
        uint256 count;

        for (uint256 i = _from; i < _to; i++) {
            Subscription storage sub = subscriptions[i];
            if (
                sub.active
                && block.timestamp >= sub.nextExecution
                && balances[sub.donor] >= sub.amount
                && (sub.maxExecutions == 0 || sub.totalExecuted < sub.maxExecutions)
            ) {
                temp[count++] = i;
            }
        }

        // Trim to actual count
        uint256[] memory result = new uint256[](count);
        for (uint256 i = 0; i < count; i++) {
            result[i] = temp[i];
        }
        return result;
    }
}
