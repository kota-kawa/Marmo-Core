import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

class ApprovalCenterPage extends StatefulWidget {
  const ApprovalCenterPage({super.key});

  @override
  State<ApprovalCenterPage> createState() => _ApprovalCenterPageState();
}

class _ApprovalCenterPageState extends State<ApprovalCenterPage> {
  final supabase = Supabase.instance.client;
  List _pendingUsers = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _fetchPending();
  }

  Future<void> _fetchPending() async {
    final res = await supabase.from('clients').select().or('status.eq.pending,status.is.null');
    setState(() {
      _pendingUsers = res as List;
      _isLoading = false;
    });
  }

  Future<void> _approveUser(String id) async {
    await supabase.from('clients').update({'status': 'active'}).eq('id', id);
    _fetchPending();
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('User Berhasil Diaktifkan!')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('APPROVAL CENTER')),
      body: _isLoading 
        ? const Center(child: CircularProgressIndicator())
        : _pendingUsers.isEmpty
          ? const Center(child: Text('Tidak ada antrean pendaftaran'))
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _pendingUsers.length,
              itemBuilder: (context, index) {
                final user = _pendingUsers[index];
                return Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: const Color(0xFF18181B),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: const Color(0xFF27272A)),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(user['name'] ?? 'No Name', style: const TextStyle(fontWeight: FontWeight.bold)),
                            Text(user['email'] ?? '', style: const TextStyle(fontSize: 12, color: Colors.white38)),
                          ],
                        ),
                      ),
                      ElevatedButton(
                        onPressed: () => _approveUser(user['id']),
                        style: ElevatedButton.styleFrom(backgroundColor: Colors.blue, foregroundColor: Colors.white),
                        child: const Text('APPROVE'),
                      ),
                    ],
                  ),
                );
              },
            ),
    );
  }
}
