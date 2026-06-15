import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:intl/intl.dart';
import 'approval_center.dart';
import 'token_audit_page.dart';

class AdminDashboard extends StatefulWidget {
  const AdminDashboard({super.key});

  @override
  State<AdminDashboard> createState() => _AdminDashboardState();
}

class _AdminDashboardState extends State<AdminDashboard> {
  final supabase = Supabase.instance.client;
  bool _isLoading = true;
  int _pendingUsers = 0;
  int _activeUsers = 0;
  double _totalRevenue = 0.0;
  String _adminEmail = '';
  final currencyFormat = NumberFormat.currency(locale: 'id_ID', symbol: 'Rp ', decimalDigits: 0);

  @override
  void initState() {
    super.initState();
    _fetchData();
  }

  Future<void> _fetchData() async {
    try {
      final user = supabase.auth.currentUser;
      
      // Fetch Clients Stats
      final clientsRes = await supabase.from('clients').select('status');
      final clients = clientsRes as List;
      
      // Fetch Revenue from Orders
      final ordersRes = await supabase.from('orders').select('total_amount');
      final orders = ordersRes as List;
      double revenue = 0.0;
      for (var order in orders) {
        revenue += (double.tryParse(order['total_amount'].toString()) ?? 0.0);
      }
      
      setState(() {
        _adminEmail = user?.email ?? 'Unknown Admin';
        _pendingUsers = clients.where((c) => c['status'] == 'pending' || c['status'] == null).length;
        _activeUsers = clients.where((c) => c['status'] == 'active').length;
        _totalRevenue = revenue;
        _isLoading = false;
      });
    } catch (e) {
      debugPrint('Error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF000000), // Pure Black for Web standard
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Row(
          children: [
            Image.asset('assets/logo.png', height: 28), // Branded Petir Icon
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('TOKCER AI', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16, letterSpacing: 1)),
                Text('CORE COMMAND CENTER', style: TextStyle(color: Colors.white24, fontSize: 8, fontWeight: FontWeight.bold, letterSpacing: 2)),
              ],
            ),
          ],
        ),
        actions: [
          // Elegant Logout Button
          Padding(
            padding: const EdgeInsets.only(right: 16.0),
            child: IconButton(
              onPressed: () => _handleLogout(context),
              icon: const Icon(Icons.power_settings_new_rounded, color: Colors.white24, size: 22),
              tooltip: 'Exit System',
            ),
          ),
        ],
      ),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator(color: Color(0xFF3B82F6)))
        : RefreshIndicator(
            onRefresh: _fetchData,
            color: const Color(0xFF3B82F6),
            backgroundColor: const Color(0xFF18181B),
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
              children: [
                // Real Revenue Card
                _buildRevenueCard('TOTAL REVENUE (ALL TIME)', currencyFormat.format(_totalRevenue), const Color(0xFF10B981)),
                const SizedBox(height: 24),
                
                // Users Stats Row
                Row(
                  children: [
                    Expanded(child: _buildSmallStatCard('ACTIVE USERS', _activeUsers.toString(), const Color(0xFF3B82F6))),
                    const SizedBox(width: 16),
                    Expanded(child: _buildSmallStatCard('PENDING', _pendingUsers.toString(), const Color(0xFFF97316))),
                  ],
                ),
                
                const SizedBox(height: 32),
                const Text('QUICK COMMANDS', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 2, color: Colors.white38)),
                const SizedBox(height: 16),
                
                _buildMenuTile(
                  Icons.verified_user_rounded, 
                  'Approval Center', 
                  'Verify $_pendingUsers registration requests', 
                  badge: _pendingUsers > 0 ? _pendingUsers.toString() : null,
                  onTap: () => Navigator.push(context, MaterialPageRoute(builder: (context) => const ApprovalCenterPage())),
                ),
                _buildMenuTile(
                  Icons.bolt_rounded, // Better Petir Icon for Audit
                  'Token Audit & Billing', 
                  'Monitor DeepSeek-V4 live consumption',
                  onTap: () => Navigator.push(context, MaterialPageRoute(builder: (context) => const TokenAuditPage())),
                ),
                _buildMenuTile(
                  Icons.calculate_rounded, 
                  'HPP Calculator', 
                  'Review business strategies',
                  onTap: () {},
                ),
                
                const SizedBox(height: 40),
                // Minimalist Profile Footer
                Center(
                  child: Column(
                    children: [
                      const Icon(Icons.shield_rounded, color: Colors.white10, size: 32),
                      const SizedBox(height: 8),
                      Text(_adminEmail, style: const TextStyle(fontSize: 10, color: Colors.white24, fontWeight: FontWeight.bold)),
                      const Text('SUPER ADMIN PRIVILEGES ACTIVE', style: TextStyle(fontSize: 8, color: Colors.white10, letterSpacing: 1.5, fontWeight: FontWeight.w900)),
                    ],
                  ),
                ),
              ],
            ),
          ),
    );
  }

  void _handleLogout(BuildContext context) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF18181B),
        title: const Text('Exit System?', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
        content: const Text('Are you sure you want to logout from Core Command?', style: TextStyle(color: Colors.white70, fontSize: 13)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('CANCEL', style: TextStyle(color: Colors.white38))),
          TextButton(
            onPressed: () => Navigator.pop(context, true), 
            child: const Text('LOGOUT', style: TextStyle(color: Colors.redAccent, fontWeight: FontWeight.bold))
          ),
        ],
      ),
    );
    if (confirm == true) {
      await supabase.auth.signOut();
    }
  }

  Widget _buildRevenueCard(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: const Color(0xFF18181B),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.white.withOpacity(0.05)),
        gradient: LinearGradient(
          colors: [const Color(0xFF18181B), const Color(0xFF111114)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 2)),
          const SizedBox(height: 12),
          Text(value, style: const TextStyle(fontSize: 32, fontWeight: FontWeight.w900, color: Colors.white, letterSpacing: -1)),
          const SizedBox(height: 8),
          const Row(
            children: [
              Icon(Icons.trending_up_rounded, color: Colors.green, size: 14),
              SizedBox(width: 4),
              Text('REAL-TIME DATABASE SYNCED', style: TextStyle(fontSize: 8, color: Colors.white24, fontWeight: FontWeight.bold, letterSpacing: 1)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSmallStatCard(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF18181B),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withOpacity(0.03)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: TextStyle(color: color, fontSize: 9, fontWeight: FontWeight.w900, letterSpacing: 1.5)),
          const SizedBox(height: 8),
          Text(value, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w900, color: Colors.white)),
        ],
      ),
    );
  }

  Widget _buildMenuTile(IconData icon, String title, String subtitle, {String? badge, VoidCallback? onTap}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF18181B),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFF27272A)),
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
        leading: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(color: Colors.black, borderRadius: BorderRadius.circular(12)),
          child: Icon(icon, color: const Color(0xFF3B82F6), size: 20),
        ),
        title: Text(title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, letterSpacing: 0.5)),
        subtitle: Text(subtitle, style: const TextStyle(fontSize: 11, color: Colors.white38)),
        trailing: badge != null 
          ? Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(color: const Color(0xFF2563EB), borderRadius: BorderRadius.circular(8)),
              child: Text(badge, style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w900)),
            )
          : const Icon(Icons.arrow_forward_ios_rounded, color: Colors.white12, size: 14),
        onTap: onTap,
      ),
    );
  }
}
