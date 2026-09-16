import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/operation.dart';
import '../services/market_api.dart';
import 'corporate_events_screen.dart';
import 'paper_trading_screen.dart';
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
  static const _pageSize = 50;
  final List<InvestmentOperation> _operations = [];
  final ScrollController _scroll = ScrollController();

  bool _loading = true;
  bool _loadingMore = false;
  bool _hasMore = false;
  int _offset = 0;
  int _total = 0;
  String? _error;

  @override
  void initState() {
    super.initState();
    _scroll.addListener(_onScroll);
    _load();
  }

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scroll.position.pixels >= _scroll.position.maxScrollExtent - 300) {
      _loadMore();
    }
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final page = await widget.api.getOperations(limit: _pageSize, offset: 0);
      if (!mounted) return;
      setState(() {
        _operations
          ..clear()
          ..addAll(page.items);
        _offset = page.nextOffset ?? _operations.length;
        _hasMore = page.hasMore;
        _total = page.total;
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

  Future<void> _loadMore() async {
    if (_loadingMore || !_hasMore) return;
    setState(() => _loadingMore = true);
    try {
      final page =
          await widget.api.getOperations(limit: _pageSize, offset: _offset);
      if (!mounted) return;
      setState(() {
        _operations.addAll(page.items);
        _offset = page.nextOffset ?? _operations.length;
        _hasMore = page.hasMore;
        _total = page.total;
      });
    } catch (_) {
      // Silencioso: el usuario puede reintentar con pull-to-refresh.
    } finally {
      if (mounted) setState(() => _loadingMore = false);
    }
  }

  Future<void> _importExport() async {
    final action = await showModalBottomSheet<String>(
      context: context,
      builder: (_) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.download),
              title: const Text('Exportar (JSON)'),
              onTap: () => Navigator.pop(context, 'export_json'),
            ),
            ListTile(
              leading: const Icon(Icons.table_view),
              title: const Text('Exportar (CSV)'),
              onTap: () => Navigator.pop(context, 'export_csv'),
            ),
            ListTile(
              leading: const Icon(Icons.upload),
              title: const Text('Importar (pegar JSON/CSV)'),
              onTap: () => Navigator.pop(context, 'import'),
            ),
          ],
        ),
      ),
    );
    if (action == 'export_json') {
      await _export('json');
    } else if (action == 'export_csv') {
      await _export('csv');
    } else if (action == 'import') {
      await _import();
    }
  }

  Future<void> _export(String format) async {
    try {
      final content = await widget.api.exportOperations(format: format);
      await Clipboard.setData(ClipboardData(text: content));
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Exportación $format copiada al portapapeles')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No se pudo exportar: $e')),
      );
    }
  }

  Future<void> _import() async {
    final result = await showDialog<ImportResult>(
      context: context,
      builder: (_) => _ImportDialog(api: widget.api),
    );
    if (result == null) return;
    await _load();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          'Importadas ${result.created}, omitidas ${result.skipped}, '
          'con error ${result.failed}',
        ),
      ),
    );
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
          IconButton(
            onPressed: _importExport,
            icon: const Icon(Icons.import_export),
            tooltip: 'Importar / exportar',
          ),
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'corporate') {
                Navigator.of(context).push(MaterialPageRoute(
                  builder: (_) => CorporateEventsScreen(api: widget.api),
                ));
              } else if (value == 'paper') {
                Navigator.of(context).push(MaterialPageRoute(
                  builder: (_) => PaperTradingScreen(api: widget.api),
                ));
              }
            },
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'corporate', child: Text('Eventos corporativos')),
              PopupMenuItem(value: 'paper', child: Text('Paper trading')),
            ],
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
        controller: _scroll,
        padding: const EdgeInsets.all(12),
        itemCount: _operations.length + 2,
        itemBuilder: (context, index) {
          if (index == 0) {
            return Card(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Text(
                  'Libro fiscal manual, separado de la cartera simulada. '
                  'Mostrando ${_operations.length} de $_total operaciones.',
                  style: const TextStyle(fontSize: 12),
                ),
              ),
            );
          }
          if (index == _operations.length + 1) {
            if (_loadingMore) {
              return const Padding(
                padding: EdgeInsets.all(16),
                child: Center(child: CircularProgressIndicator()),
              );
            }
            return const SizedBox(height: 24);
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
  final _fx = TextEditingController();
  final _notes = TextEditingController();
  String _side = 'BUY';
  String _fxSource = 'ECB';
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
    final fxText = _fx.text.trim().replaceAll(',', '.');
    // Con fuente ECB y sin tasa, el backend resuelve el cambio automáticamente.
    final autoFx = _fxSource == 'ECB' && fxText.isEmpty;
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
        fxRateToEur: autoFx ? null : fxText,
        fxSource: _fxSource,
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
                DropdownButtonFormField<String>(
                  initialValue: _fxSource,
                  decoration: const InputDecoration(labelText: 'Fuente del cambio'),
                  items: const [
                    DropdownMenuItem(value: 'ECB', child: Text('Automático (BCE)')),
                    DropdownMenuItem(value: 'USER', child: Text('Manual')),
                  ],
                  onChanged: (value) => setState(() => _fxSource = value ?? 'ECB'),
                ),
                _decimalField(
                  _fx,
                  _fxSource == 'ECB'
                      ? 'Cambio a EUR (opcional, se resuelve solo)'
                      : 'Cambio a EUR',
                  (value) {
                    if (_fxSource == 'ECB' && (value ?? '').trim().isEmpty) {
                      return null;
                    }
                    return _positive(value);
                  },
                  helper: '1 unidad de la divisa = N EUR',
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


class _ImportDialog extends StatefulWidget {
  const _ImportDialog({required this.api});

  final MarketApi api;

  @override
  State<_ImportDialog> createState() => _ImportDialogState();
}

class _ImportDialogState extends State<_ImportDialog> {
  final _content = TextEditingController();
  String _format = 'json';
  String _broker = 'none';
  bool _busy = false;
  String? _message;

  @override
  void dispose() {
    _content.dispose();
    super.dispose();
  }

  Future<void> _run({required bool dryRun}) async {
    if (_content.text.trim().isEmpty) {
      setState(() => _message = 'Pega el contenido a importar');
      return;
    }
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      final result = _broker == 'none'
          ? await widget.api.importOperations(
              content: _content.text,
              format: _format,
              dryRun: dryRun,
            )
          : await widget.api.importBrokerCsv(
              broker: _broker,
              content: _content.text,
              dryRun: dryRun,
            );
      if (!mounted) return;
      if (dryRun) {
        setState(() {
          _busy = false;
          _message = 'Previsualización: ${result.created} válidas, '
              '${result.skipped} duplicadas, ${result.failed} con error';
        });
      } else {
        Navigator.of(context).pop(result);
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _message = 'Error: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Importar operaciones'),
      content: SizedBox(
        width: 520,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            DropdownButtonFormField<String>(
              initialValue: _broker,
              decoration: const InputDecoration(labelText: 'Origen'),
              items: const [
                DropdownMenuItem(value: 'none', child: Text('Genérico (JSON/CSV propio)')),
                DropdownMenuItem(value: 'generic', child: Text('Broker: genérico')),
                DropdownMenuItem(
                    value: 'trade_republic', child: Text('Broker: Trade Republic')),
                DropdownMenuItem(value: 'revolut', child: Text('Broker: Revolut')),
              ],
              onChanged: (value) => setState(() => _broker = value ?? 'none'),
            ),
            const SizedBox(height: 12),
            if (_broker == 'none')
              DropdownButtonFormField<String>(
                initialValue: _format,
                decoration: const InputDecoration(labelText: 'Formato'),
                items: const [
                  DropdownMenuItem(value: 'json', child: Text('JSON')),
                  DropdownMenuItem(value: 'csv', child: Text('CSV')),
                ],
                onChanged: (value) => setState(() => _format = value ?? 'json'),
              ),
            const SizedBox(height: 12),
            TextField(
              controller: _content,
              maxLines: 8,
              decoration: const InputDecoration(
                labelText: 'Contenido',
                helperText: 'Cada operación necesita externalId único para evitar duplicados',
                border: OutlineInputBorder(),
              ),
            ),
            if (_message != null) ...[
              const SizedBox(height: 12),
              Text(_message!, style: const TextStyle(fontSize: 12)),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _busy ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancelar'),
        ),
        TextButton(
          onPressed: _busy ? null : () => _run(dryRun: true),
          child: const Text('Previsualizar'),
        ),
        FilledButton(
          onPressed: _busy ? null : () => _run(dryRun: false),
          child: const Text('Importar'),
        ),
      ],
    );
  }
}
