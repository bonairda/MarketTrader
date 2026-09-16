import 'package:flutter/material.dart';

import '../models/operation.dart';
import '../services/market_api.dart';
import 'tax_report_screen.dart';

/// Libro fiscal de compras y ventas. Es independiente de la cartera simulada:
/// su objetivo es trazabilidad y cálculo FIFO, no ejecutar órdenes reales.
class OperationsScreen extends StatefulWidget {
  const OperationsScreen({super.key, required this.api});

  final MarketApi api;

  @override
  State<OperationsScreen> createState() => _OperationsScreenState();
}

class _OperationsScreenState extends State<OperationsScreen> {
  List<InvestmentOperation> _operations = [];
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
      final operations = await widget.api.getOperations(limit: 500);
      if (!mounted) return;
      setState(() {
        _operations = operations;
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

  Future<void> _add() async {
    final input = await showDialog<NewInvestmentOperation>(
      context: context,
      builder: (_) => const _OperationDialog(),
    );
    if (input == null) return;
    try {
      await widget.api.createOperation(input);
      await _load();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Operación registrada')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No se pudo registrar: $e')),
      );
    }
  }

  Future<void> _delete(InvestmentOperation operation) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Eliminar operación'),
        content: Text(
          '¿Eliminar ${operation.side} de ${operation.quantity} '
          '${operation.assetId.toUpperCase()}?\n\n'
          'Se recalculará FIFO. Si deja una venta posterior sin saldo, '
          'el servidor rechazará el borrado.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Eliminar'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await widget.api.deleteOperation(operation.id);
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No se pudo eliminar: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Operaciones'),
        actions: [
          IconButton(
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => TaxReportScreen(api: widget.api)),
            ),
            icon: const Icon(Icons.receipt_long),
            tooltip: 'Informe fiscal',
          ),
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _add,
        tooltip: 'Registrar compra o venta',
        child: const Icon(Icons.add),
      ),
      body: _body(),
    );
  }

  Widget _body() {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) return Center(child: Text('Error: $_error'));
    if (_operations.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text(
            'Sin operaciones fiscales. Registra compras y ventas con el botón +.\n\n'
            'Este libro no ejecuta órdenes ni modifica la cartera simulada.',
            textAlign: TextAlign.center,
          ),
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.builder(
        padding: const EdgeInsets.all(12),
        itemCount: _operations.length + 1,
        itemBuilder: (context, index) {
          if (index == 0) {
            return const Card(
              child: Padding(
                padding: EdgeInsets.all(12),
                child: Text(
                  'Libro fiscal manual, separado de la cartera simulada. '
                  'El cambio indica cuántos EUR equivalen a 1 unidad de divisa.',
                  style: TextStyle(fontSize: 12),
                ),
              ),
            );
          }
          final operation = _operations[index - 1];
          final color = operation.isBuy ? Colors.blue.shade700 : Colors.orange.shade800;
          return Card(
            child: ListTile(
              leading: CircleAvatar(
                backgroundColor: color,
                child: Icon(
                  operation.isBuy ? Icons.south_west : Icons.north_east,
                  color: Colors.white,
                ),
              ),
              title: Text('${operation.side} · ${operation.assetId.toUpperCase()}'),
              subtitle: Text(
                '${operation.tradeDate} · ${operation.quantity} uds.\n'
                '${operation.grossAmountOriginal} ${operation.currency} + '
                '${operation.feesOriginal} comisión · ${operation.cashAmountEur} EUR',
              ),
              isThreeLine: true,
              trailing: IconButton(
                onPressed: () => _delete(operation),
                icon: const Icon(Icons.delete_outline),
                tooltip: 'Eliminar',
              ),
            ),
          );
        },
      ),
    );
  }
}

class _OperationDialog extends StatefulWidget {
  const _OperationDialog();

  @override
  State<_OperationDialog> createState() => _OperationDialogState();
}

class _OperationDialogState extends State<_OperationDialog> {
  final _formKey = GlobalKey<FormState>();
  final _asset = TextEditingController();
  final _quantity = TextEditingController();
  final _price = TextEditingController();
  final _gross = TextEditingController();
  final _fees = TextEditingController(text: '0');
  final _currency = TextEditingController(text: 'EUR');
  final _fx = TextEditingController(text: '1');
  final _fxSource = TextEditingController(text: 'USER');
  final _notes = TextEditingController();
  String _side = 'BUY';
  DateTime _date = DateTime.now();

  @override
  void dispose() {
    for (final controller in [
      _asset,
      _quantity,
      _price,
      _gross,
      _fees,
      _currency,
      _fx,
      _fxSource,
      _notes,
    ]) {
      controller.dispose();
    }
    super.dispose();
  }

  String _dateText(DateTime value) =>
      '${value.year.toString().padLeft(4, '0')}-'
      '${value.month.toString().padLeft(2, '0')}-'
      '${value.day.toString().padLeft(2, '0')}';

  double? _number(String value) => double.tryParse(value.replaceAll(',', '.'));

  String? _positive(String? value) {
    final parsed = _number(value ?? '');
    return parsed == null || parsed <= 0 ? 'Debe ser mayor que 0' : null;
  }

  String? _nonNegative(String? value) {
    final parsed = _number(value ?? '');
    return parsed == null || parsed < 0 ? 'Debe ser 0 o mayor' : null;
  }

  Future<void> _pickDate() async {
    final selected = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime(1980),
      lastDate: DateTime.now(),
    );
    if (selected != null) setState(() => _date = selected);
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    final gross = _gross.text.trim().replaceAll(',', '.');
    Navigator.of(context).pop(
      NewInvestmentOperation(
        assetId: _asset.text.trim(),
        side: _side,
        tradeDate: _dateText(_date),
        quantity: _quantity.text.trim().replaceAll(',', '.'),
        unitPriceOriginal: _price.text.trim().replaceAll(',', '.'),
        grossAmountOriginal: gross,
        feesOriginal: _fees.text.trim().replaceAll(',', '.'),
        currency: _currency.text.trim().toUpperCase(),
        fxRateToEur: _fx.text.trim().replaceAll(',', '.'),
        fxSource: _fxSource.text.trim().toUpperCase(),
        notes: _notes.text.trim(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Registrar operación'),
      content: SizedBox(
        width: 480,
        child: SingleChildScrollView(
          child: Form(
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
                  onChanged: (value) => setState(() => _side = value ?? 'BUY'),
                ),
                TextFormField(
                  controller: _asset,
                  decoration: const InputDecoration(
                    labelText: 'Activo',
                    helperText: 'btcusdt, stock:AAPL o fx:EUR/USD',
                  ),
                  validator: (value) => (value ?? '').trim().isEmpty
                      ? 'Introduce el activo'
                      : null,
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Fecha fiscal'),
                  subtitle: Text(_dateText(_date)),
                  trailing: const Icon(Icons.calendar_month),
                  onTap: _pickDate,
                ),
                _decimalField(_quantity, 'Cantidad', _positive),
                _decimalField(_price, 'Precio unitario original', _positive),
                _decimalField(
                  _gross,
                  'Importe bruto original',
                  _positive,
                  helper: 'Introduce el importe exacto comunicado por el broker',
                ),
                _decimalField(_fees, 'Comisiones originales', _nonNegative),
                TextFormField(
                  controller: _currency,
                  decoration: const InputDecoration(labelText: 'Divisa (EUR, USD, USDT...)'),
                  validator: (value) => (value ?? '').trim().length < 3
                      ? 'Código de divisa no válido'
                      : null,
                ),
                _decimalField(
                  _fx,
                  'Cambio a EUR',
                  _positive,
                  helper: '1 unidad de la divisa = N EUR',
                ),
                TextFormField(
                  controller: _fxSource,
                  decoration: const InputDecoration(labelText: 'Fuente del cambio'),
                ),
                TextFormField(
                  controller: _notes,
                  decoration: const InputDecoration(labelText: 'Notas (opcional)'),
                  maxLines: 2,
                ),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancelar')),
        FilledButton(onPressed: _submit, child: const Text('Guardar')),
      ],
    );
  }

  Widget _decimalField(
    TextEditingController controller,
    String label,
    String? Function(String?) validator, {
    String? helper,
  }) =>
      TextFormField(
        controller: controller,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        decoration: InputDecoration(labelText: label, helperText: helper),
        validator: validator,
      );
}
