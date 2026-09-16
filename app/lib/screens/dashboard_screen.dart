import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/dashboard.dart';
import '../services/market_api.dart';
import 'asset_detail_screen.dart';

/// Pantalla de inicio: resumen del mercado seguido (contadores, top movers,
/// más volátiles).
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key, required this.api});

  final MarketApi api;

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final _priceFormat = NumberFormat('#,##0.00');
  final _pctFormat = NumberFormat('+#,##0.00;-#,##0.00');

  Dashboard? _dashboard;
  bool _loading = true;
  String? _error;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _load();
    // Refresco periódico moderado (el backend ya cachea 10 s).
    _timer = Timer.periodic(const Duration(seconds: 15), (_) => _load(silent: true));
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _load({bool silent = false}) async {
    if (!silent) setState(() => _loading = true);
    try {
      final dashboard = await widget.api.getDashboard();
      if (!mounted) return;
      setState(() {
        _dashboard = dashboard;
        _loading = false;
        _error = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  void _openDetail(String symbol) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => AssetDetailScreen(symbol: symbol, api: widget.api),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off, size: 48),
              const SizedBox(height: 12),
              Text('No se pudo cargar el dashboard.\n$_error',
                  textAlign: TextAlign.center),
              const SizedBox(height: 12),
              FilledButton(onPressed: () => _load(), child: const Text('Reintentar')),
            ],
          ),
        ),
      );
    }

    final d = _dashboard!;
    return RefreshIndicator(
      onRefresh: () => _load(),
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          _summaryCard(d),
          const SizedBox(height: 12),
          _moversSection('Mayores subidas', d.gainers, Icons.trending_up),
          const SizedBox(height: 12),
          _moversSection('Mayores bajadas', d.losers, Icons.trending_down),
          const SizedBox(height: 12),
          _volatileSection(d.mostVolatile),
        ],
      ),
    );
  }

  Widget _summaryCard(Dashboard d) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _stat('Seguidos', '${d.tracked}'),
            _stat('Suben', '${d.gainers.length}'),
            _stat('Bajan', '${d.losers.length}'),
          ],
        ),
      ),
    );
  }

  Widget _stat(String label, String value) {
    return Column(
      children: [
        Text(value, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
        Text(label, style: const TextStyle(fontSize: 12)),
      ],
    );
  }

  Widget _moversSection(String title, List<AssetSummary> items, IconData icon) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 18),
                const SizedBox(width: 8),
                Text(title, style: Theme.of(context).textTheme.titleMedium),
              ],
            ),
            const SizedBox(height: 4),
            if (items.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 8),
                child: Text('Sin datos'),
              )
            else
              ...items.map(_moverRow),
          ],
        ),
      ),
    );
  }

  Widget _moverRow(AssetSummary s) {
    final change = s.changePercent ?? 0;
    final positive = change >= 0;
    final color = positive ? Colors.green.shade700 : Colors.red.shade700;
    return ListTile(
      dense: true,
      contentPadding: EdgeInsets.zero,
      title: Text(s.symbol.toUpperCase()),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (s.price != null)
            Text(_priceFormat.format(s.price), style: const TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(width: 12),
          Icon(positive ? Icons.arrow_drop_up : Icons.arrow_drop_down, color: color),
          Text('${_pctFormat.format(change)}%', style: TextStyle(color: color)),
        ],
      ),
      onTap: () => _openDetail(s.symbol),
    );
  }

  Widget _volatileSection(List<AssetSummary> items) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.show_chart, size: 18),
                const SizedBox(width: 8),
                Text('Más volátiles', style: Theme.of(context).textTheme.titleMedium),
              ],
            ),
            const SizedBox(height: 4),
            if (items.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 8),
                child: Text('Sin datos'),
              )
            else
              ...items.map(
                (s) => ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  title: Text(s.symbol.toUpperCase()),
                  trailing: Text('σ ${(_priceFormat.format(s.volatility ?? 0))}%'),
                  onTap: () => _openDetail(s.symbol),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
