import 'package:flutter/material.dart';

import '../models/paper_trading.dart';
import '../services/market_api.dart';

/// Paper trading (Alpaca): órdenes simuladas sin dinero real.
/// Solo está operativo si el backend tiene credenciales de paper configuradas.
class PaperTradingScreen extends StatefulWidget {
  const PaperTradingScreen({super.key, required this.api});

  final MarketApi api;

  @override
  State<PaperTradingScreen> createState() => _PaperTradingScreenState();
}

class _PaperTradingScreenState extends State<PaperTradingScreen> {
  PaperTradingStatus? _status;
  List<PaperOrder> _orders = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final status = await widget.api.getPaperStatus();
      List<PaperOrder> orders = [];
      if (status.enabled) {
        orders = await widget.api.getPaperOrders();
      }
      if (!mounted) return;
      setState(() {
        _status = status;
        _orders = orders;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _newOrder() async {
    final placed = await showDialog<bool>(
      context: context,
      builder: (_) => _PaperOrderDialog(api: widget.api),
    );
    if (placed == true) await _load();
  }

  @override
  Widget build(BuildContext context) {
    final enabled = _status?.enabled ?? false;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Paper trading'),
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh))],
      ),
      floatingActionButton: enabled
          ? FloatingActionButton.extended(
              onPressed: _newOrder,
              icon: const Icon(Icons.add),
              label: const Text('Orden simulada'),
            )
          : null,
      body: _body(),
    );
  }

  Widget _body() {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) return Center(child: Text('Error: $_error'));
    final enabled = _status?.enabled ?? false;
    if (!enabled) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text(
            'Paper trading no está habilitado.\n\n'
            'Configura las credenciales de Alpaca (host paper) en el servidor. '
            'Nunca se opera con dinero real.',
            textAlign: TextAlign.center,
          ),
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          const Card(
            child: Padding(
              padding: EdgeInsets.all(12),
              child: Text(
                'Modo simulado (paper). Las órdenes no usan dinero real y sirven '
                'para practicar el flujo de compra/venta.',
                style: TextStyle(fontSize: 12),
              ),
            ),
          ),
          const SizedBox(height: 8),
          Text('Órdenes recientes',
              style: Theme.of(context).textTheme.titleMedium),
          if (_orders.isEmpty)
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text('Aún no hay órdenes.'),
            ),
          ..._orders.map(
            (o) => Card(
              child: ListTile(
                title: Text('${o.side} ${o.quantity} ${o.symbol}'),
                subtitle: Text('Estado: ${o.status}'),
                trailing: Text(o.submittedAt?.split('T').first ?? ''),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PaperOrderDialog extends StatefulWidget {
  const _PaperOrderDialog({required this.api});

  final MarketApi api;

  @override
  State<_PaperOrderDialog> createState() => _PaperOrderDialogState();
}

class _PaperOrderDialogState extends State<_PaperOrderDialog> {
  final _formKey = GlobalKey<FormState>();
  final _asset = TextEditingController(text: 'stock:');
  final _quantity = TextEditingController();
  String _side = 'BUY';
  bool _confirm = false;
  bool _busy = false;

  @override
  void dispose() {
    _asset.dispose();
    _quantity.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (!_confirm) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Marca la confirmación para enviar')),
      );
      return;
    }
    setState(() => _busy = true);
    try {
      await widget.api.submitPaperOrder(
        assetId: _asset.text.trim(),
        side: _side,
        quantity: _quantity.text.trim().replaceAll(',', '.'),
        confirm: true,
      );
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } catch (e) {
      if (!mounted) return;
      setState(() => _busy = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No se pudo enviar: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Orden simulada (paper)'),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            DropdownButtonFormField<String>(
              initialValue: _side,
              decoration: const InputDecoration(labelText: 'Tipo'),
              items: const [
                DropdownMenuItem(value: 'BUY', child: Text('Compra')),
                DropdownMenuItem(value: 'SELL', child: Text('Venta')),
              ],
              onChanged: (v) => setState(() => _side = v ?? 'BUY'),
            ),
            TextFormField(
              controller: _asset,
              decoration: const InputDecoration(
                labelText: 'Activo',
                helperText: 'Solo acciones: stock:AAPL',
              ),
              validator: (v) => (v ?? '').startsWith('stock:') &&
                      (v ?? '').length > 'stock:'.length
                  ? null
                  : 'Formato stock:TICKER',
            ),
            TextFormField(
              controller: _quantity,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(labelText: 'Cantidad'),
              validator: (v) =>
                  (double.tryParse((v ?? '').replaceAll(',', '.')) ?? 0) <= 0
                      ? 'Debe ser mayor que 0'
                      : null,
            ),
            CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              value: _confirm,
              onChanged: (v) => setState(() => _confirm = v ?? false),
              title: const Text('Confirmo esta orden simulada'),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _busy ? null : () => Navigator.of(context).pop(false),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          onPressed: _busy ? null : _submit,
          child: const Text('Enviar'),
        ),
      ],
    );
  }
}
