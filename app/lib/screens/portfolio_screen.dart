import 'package:flutter/material.dart';

import '../models/derived_portfolio.dart';
import '../models/portfolio.dart';
import '../services/market_api.dart';

/// Cartera simulada: posiciones valoradas con precio en vivo + resumen P&L.
class PortfolioScreen extends StatefulWidget {
  const PortfolioScreen({super.key, required this.api});

  final MarketApi api;

  @override
  State<PortfolioScreen> createState() => _PortfolioScreenState();
}

class _PortfolioScreenState extends State<PortfolioScreen> {
  Portfolio? _portfolio;
  DerivedPortfolio? _derived;
  bool _showDerived = true;
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
      if (_showDerived) {
        final derived = await widget.api.getDerivedPortfolio();
        if (!mounted) return;
        setState(() {
          _derived = derived;
          _loading = false;
        });
      } else {
        final portfolio = await widget.api.getPortfolio();
        if (!mounted) return;
        setState(() {
          _portfolio = portfolio;
          _loading = false;
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _openAddPosition() async {
    final result = await showDialog<_PositionInput>(
      context: context,
      builder: (_) => const _AddPositionDialog(),
    );
    if (result == null) return;
    try {
      await widget.api.addPosition(
        assetId: result.assetId,
        quantity: result.quantity,
        averagePrice: result.averagePrice,
      );
      await _load();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Posición añadida')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error añadiendo posición: $e')),
      );
    }
  }

  Future<void> _deletePosition(PortfolioPosition p) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Eliminar posición'),
        content: Text('¿Eliminar ${p.assetId.toUpperCase()} de la cartera?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Eliminar'),
          ),
        ],
      ),
    );
    if (confirm != true) return;
    try {
      await widget.api.deletePosition(p.id);
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error eliminando: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Cartera'),
        actions: [
          IconButton(
            onPressed: _load,
            icon: const Icon(Icons.refresh),
            tooltip: 'Refrescar',
          ),
        ],
      ),
      floatingActionButton: _showDerived
          ? null
          : FloatingActionButton(
              onPressed: _openAddPosition,
              tooltip: 'Añadir posición',
              child: const Icon(Icons.add),
            ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: SegmentedButton<bool>(
              segments: const [
                ButtonSegment(value: true, label: Text('Derivada (libro)')),
                ButtonSegment(value: false, label: Text('Simulada')),
              ],
              selected: {_showDerived},
              onSelectionChanged: (s) {
                setState(() => _showDerived = s.first);
                _load();
              },
            ),
          ),
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(child: Text('Error: $_error'));
    }
    if (_showDerived) {
      return _buildDerived(_derived!);
    }
    final portfolio = _portfolio!;
    if (portfolio.positions.isEmpty) {
      return const Center(
        child: Text('Sin posiciones. Añade una con el botón +.'),
      );
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          _SummaryCard(summary: portfolio.summary),
          const SizedBox(height: 12),
          ...portfolio.positions.map(
            (p) => _PositionTile(position: p, onDelete: () => _deletePosition(p)),
          ),
        ],
      ),
    );
  }

  Widget _buildDerived(DerivedPortfolio portfolio) {
    if (portfolio.positions.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text(
            'Sin posiciones abiertas en el libro de operaciones.',
            textAlign: TextAlign.center,
          ),
        ),
      );
    }
    final pnl = double.tryParse(portfolio.totalPnlEur) ?? 0;
    final pnlColor = pnl >= 0 ? Colors.green.shade700 : Colors.red.shade700;
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Resumen (EUR)',
                      style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  _kv('Coste total', '${portfolio.totalCostEur} EUR'),
                  _kv('Valor de mercado', '${portfolio.totalValueEur} EUR'),
                  _kv(
                    'P&L',
                    '${pnl >= 0 ? '+' : ''}${portfolio.totalPnlEur} EUR'
                        '${portfolio.totalPnlPercent != null ? ' (${portfolio.totalPnlPercent}%)' : ''}',
                    color: pnlColor,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          ...portfolio.positions.map((p) {
            final positionPnl = double.tryParse(p.pnlEur ?? '');
            return Card(
              child: ListTile(
                title: Text(p.assetId.toUpperCase()),
                subtitle: Text(
                  '${p.quantity} uds · coste medio ${p.avgCostEur} EUR\n'
                  'Valor ${p.marketValueEur ?? '—'} EUR',
                ),
                isThreeLine: true,
                trailing: Text(
                  p.pnlEur == null
                      ? '—'
                      : '${positionPnl != null && positionPnl >= 0 ? '+' : ''}${p.pnlEur} EUR',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: positionPnl == null
                        ? Colors.grey
                        : (positionPnl >= 0
                            ? Colors.green.shade700
                            : Colors.red.shade700),
                  ),
                ),
              ),
            );
          }),
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Text(
              portfolio.note,
              style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic),
            ),
          ),
        ],
      ),
    );
  }

  Widget _kv(String label, String value, {Color? color}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label),
          Text(value,
              style: TextStyle(fontWeight: FontWeight.w600, color: color)),
        ],
      ),
    );
  }
}

/// Tarjeta con el resumen global de la cartera.
class _SummaryCard extends StatelessWidget {
  const _SummaryCard({required this.summary});

  final PortfolioSummary summary;

  String _money(double v) => v.toStringAsFixed(2);
  String _pct(double? v) =>
      v == null ? '—' : '${v >= 0 ? '+' : ''}${v.toStringAsFixed(2)}%';

  @override
  Widget build(BuildContext context) {
    final pnlColor =
        summary.totalPnl >= 0 ? Colors.green.shade700 : Colors.red.shade700;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Resumen', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            _row('Coste total', _money(summary.totalCost)),
            _row('Valor de mercado', _money(summary.totalValue)),
            _row(
              'P&L',
              '${summary.totalPnl >= 0 ? '+' : ''}${_money(summary.totalPnl)} '
                  '(${_pct(summary.totalPnlPercent)})',
              color: pnlColor,
            ),
            _row('Posiciones', '${summary.positions}'),
          ],
        ),
      ),
    );
  }

  Widget _row(String label, String value, {Color? color}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label),
          Text(value,
              style: TextStyle(fontWeight: FontWeight.w600, color: color)),
        ],
      ),
    );
  }
}

/// Fila de una posición valorada.
class _PositionTile extends StatelessWidget {
  const _PositionTile({required this.position, required this.onDelete});

  final PortfolioPosition position;
  final VoidCallback onDelete;

  String _fmt(double? v) => v == null ? '—' : v.toStringAsFixed(2);
  String _pct(double? v) =>
      v == null ? '—' : '${v >= 0 ? '+' : ''}${v.toStringAsFixed(2)}%';

  @override
  Widget build(BuildContext context) {
    final pnl = position.pnl;
    final pnlColor = pnl == null
        ? Colors.grey
        : (pnl >= 0 ? Colors.green.shade700 : Colors.red.shade700);
    return Card(
      child: ListTile(
        title: Text(position.assetId.toUpperCase()),
        subtitle: Text(
          '${position.quantity} @ ${_fmt(position.averagePrice)}  ·  '
          'Actual: ${_fmt(position.currentPrice)}',
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  position.pnl == null
                      ? '—'
                      : '${pnl! >= 0 ? '+' : ''}${_fmt(pnl)}',
                  style: TextStyle(fontWeight: FontWeight.bold, color: pnlColor),
                ),
                Text(_pct(position.pnlPercent),
                    style: TextStyle(fontSize: 12, color: pnlColor)),
              ],
            ),
            IconButton(
              onPressed: onDelete,
              icon: const Icon(Icons.delete_outline),
              tooltip: 'Eliminar',
            ),
          ],
        ),
      ),
    );
  }
}

/// Datos del diálogo de nueva posición.
class _PositionInput {
  const _PositionInput({
    required this.assetId,
    required this.quantity,
    required this.averagePrice,
  });
  final String assetId;
  final double quantity;
  final double averagePrice;
}

class _AddPositionDialog extends StatefulWidget {
  const _AddPositionDialog();

  @override
  State<_AddPositionDialog> createState() => _AddPositionDialogState();
}

class _AddPositionDialogState extends State<_AddPositionDialog> {
  final _formKey = GlobalKey<FormState>();
  final _assetController = TextEditingController();
  final _quantityController = TextEditingController();
  final _priceController = TextEditingController();

  @override
  void dispose() {
    _assetController.dispose();
    _quantityController.dispose();
    _priceController.dispose();
    super.dispose();
  }

  double? _positive(String? v) {
    final parsed = double.tryParse((v ?? '').replaceAll(',', '.'));
    if (parsed == null || parsed <= 0) return null;
    return parsed;
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    Navigator.of(context).pop(
      _PositionInput(
        assetId: _assetController.text.trim(),
        quantity: _positive(_quantityController.text)!,
        averagePrice: _positive(_priceController.text)!,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Nueva posición'),
      content: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: _assetController,
                decoration: const InputDecoration(
                  labelText: 'Activo',
                  helperText: 'ej. btcusdt, stock:AAPL, fx:EUR/USD',
                ),
                validator: (v) =>
                    (v == null || v.trim().isEmpty) ? 'Introduce un activo' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _quantityController,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'Cantidad'),
                validator: (v) =>
                    _positive(v) == null ? 'Debe ser mayor que 0' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _priceController,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'Precio medio'),
                validator: (v) =>
                    _positive(v) == null ? 'Debe ser mayor que 0' : null,
              ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancelar'),
        ),
        FilledButton(onPressed: _submit, child: const Text('Añadir')),
      ],
    );
  }
}
