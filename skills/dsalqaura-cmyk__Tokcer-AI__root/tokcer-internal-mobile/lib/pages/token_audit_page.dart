import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class TokenAuditPage extends StatefulWidget {
  const TokenAuditPage({super.key});

  @override
  State<TokenAuditPage> createState() => _TokenAuditPageState();
}

class _TokenAuditPageState extends State<TokenAuditPage> {
  final supabase = Supabase.instance.client;
  List _logs = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _fetchLogs();
  }

  Future<void> _fetchLogs() async {
    final res = await supabase.from('ai_usage_logs').select().order('created_at', ascending: false).limit(20);
    setState(() {
      _logs = res as List;
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('TOKEN AUDIT & BILLING')),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator())
        : ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _buildSummaryRow('Input Tokens', '2.4M', Colors.blue),
              _buildSummaryRow('Output Tokens', '1.8M', const Color(0xFF10B981)),
              const SizedBox(height: 24),
              const Text('RECENT ACTIVITY', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white38)),
              const SizedBox(height: 12),
              ..._logs.map((log) => _buildLogTile(log)),
            ],
          ),
    );
  }

  Widget _buildSummaryRow(String label, String value, Color color) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(fontWeight: FontWeight.bold)),
          Text(value, style: TextStyle(color: color, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  Widget _buildLogTile(dynamic log) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF18181B),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          const Icon(Icons.bolt, color: Colors.orange, size: 16),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(log['feature'] ?? 'AI Usage', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                Text(log['model'] ?? 'DeepSeek-V3', style: const TextStyle(fontSize: 10, color: Colors.white38)),
              ],
            ),
          ),
          Text('${log['total_tokens'] ?? 0} tk', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }
}
