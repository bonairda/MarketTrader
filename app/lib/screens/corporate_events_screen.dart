import 'package:flutter/material.dart';

import '../models/corporate_event.dart';
import '../services/market_api.dart';

/// Eventos corporativos: dividendos (con retención) y splits.
class CorporateEventsScreen extends StatefulWidget {
  const CorporateEventsScreen({super.key, required this.api});

  final MarketApi api;

  @override
  State<CorporateEventsScreen> createState() => _CorporateEventsScreenState();
}

class _CorporateEventsScreenState extends State<CorporateEventsScreen> {
  List<CorporateEvent> _events = [];
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
      final events = await widget.api.getCorporateEvents();
      if (!mounted) return;
      setState(() {
        _events = events;
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
    final event = await showDialog<NewCorporateEvent>(
      context: context,
      builder: (_) => const _CorporateEventDialog(),
    );
    if (event == null) return;
    try {
      await widget.api.addCorporateEvent(event);
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No se pudo registrar: $e')),
      );
    }
  }

  Future<void> _delete(CorporateEvent event) async {
    try {
      await widget.api.deleteCorporateEvent(event.id);
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
        title: const Text('Eventos corporativos'),
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh))],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _add,
        tooltip: 'Registrar dividendo o split',
        child: const Icon(Icons.add),
      ),
      body: _body(),
    );
  }

  Widget _body() {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) return Center(child: Text('Error: $_error'));
    if (_events.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text(
            'Sin eventos corporativos. Registra dividendos (con retención) o '
            'splits con el botón +.',
            textAlign: TextAlign.center,
          ),
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.builder(
        padding: const EdgeInsets.all(12),
        itemCount: _events.length,
        itemBuilder: (context, index) {
          final event = _events[index];
          return Card(
            child: ListTile(
              leading: Icon(
                event.isDividend ? Icons.payments : Icons.call_split,
              ),
              title: Text('${event.assetId.toUpperCase()} · '
                  '${event.isDividend ? 'Dividendo' : 'Split'}'),
              subtitle: Text(
                event.isDividend
                    ? '${event.eventDate} · Bruto ${event.grossAmountEur ?? '—'} EUR · '
                        'Retención ${event.withholdingEur ?? '—'} EUR · '
                        'Neto ${event.netAmountEur ?? '—'} EUR'
                    : '${event.eventDate} · Ratio ${event.ratio}',
              ),
              isThreeLine: event.isDividend,
              trailing: IconButton(
                onPressed: () => _delete(event),
                icon: const Icon(Icons.delete_outline),
              ),
            ),
          );
        },
      ),
    );
  }
}

class _CorporateEventDialog extends StatefulWidget {
  const _CorporateEventDialog();

  @override
  State<_CorporateEventDialog> createState() => _CorporateEventDialogState();
}

class _CorporateEventDialogState extends State<_CorporateEventDialog> {
  final _formKey = GlobalKey<FormState>();
  final _asset = TextEditingController();
  final _gross = TextEditingController();
  final _withholding = TextEditingController(text: '0');
  final _currency = TextEditingController(text: 'EUR');
  final _ratio = TextEditingController();
  final _notes = TextEditingController();
  String _type = 'DIVIDEND';
  DateTime _date = DateTime.now();

  @override
  void dispose() {
    for (final c in [_asset, _gross, _withholding, _currency, _ratio, _notes]) {
      c.dispose();
    }
    super.dispose();
  }

  String _dateText(DateTime v) =>
      '${v.year.toString().padLeft(4, '0')}-'
      '${v.month.toString().padLeft(2, '0')}-'
      '${v.day.toString().padLeft(2, '0')}';

  double? _num(String v) => double.tryParse(v.replaceAll(',', '.'));

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    Navigator.of(context).pop(
      NewCorporateEvent(
        assetId: _asset.text.trim(),
        type: _type,
        eventDate: _dateText(_date),
        grossAmountOriginal:
            _type == 'DIVIDEND' ? _gross.text.trim().replaceAll(',', '.') : null,
        withholdingOriginal:
            _type == 'DIVIDEND' ? _withholding.text.trim().replaceAll(',', '.') : null,
        currency: _type == 'DIVIDEND' ? _currency.text.trim().toUpperCase() : null,
        ratio: _type == 'SPLIT' ? _ratio.text.trim().replaceAll(',', '.') : null,
        notes: _notes.text.trim(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDividend = _type == 'DIVIDEND';
    return AlertDialog(
      title: const Text('Registrar evento'),
      content: SizedBox(
        width: 460,
        child: SingleChildScrollView(
          child: Form(
            key: _formKey,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<String>(
                  initialValue: _type,
                  decoration: const InputDecoration(labelText: 'Tipo'),
                  items: const [
                    DropdownMenuItem(value: 'DIVIDEND', child: Text('Dividendo')),
                    DropdownMenuItem(value: 'SPLIT', child: Text('Split')),
                  ],
                  onChanged: (v) => setState(() => _type = v ?? 'DIVIDEND'),
                ),
                TextFormField(
                  controller: _asset,
                  decoration: const InputDecoration(
                    labelText: 'Activo',
                    helperText: 'stock:AAPL, btcusdt, ...',
                  ),
                  validator: (v) =>
                      (v ?? '').trim().isEmpty ? 'Introduce el activo' : null,
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Fecha'),
                  subtitle: Text(_dateText(_date)),
                  trailing: const Icon(Icons.calendar_month),
                  onTap: () async {
                    final picked = await showDatePicker(
                      context: context,
                      initialDate: _date,
                      firstDate: DateTime(1980),
                      lastDate: DateTime.now(),
                    );
                    if (picked != null) setState(() => _date = picked);
                  },
                ),
                if (isDividend) ...[
                  TextFormField(
                    controller: _gross,
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(labelText: 'Bruto (divisa)'),
                    validator: (v) => (_num(v ?? '') ?? 0) <= 0
                        ? 'Debe ser mayor que 0'
                        : null,
                  ),
                  TextFormField(
                    controller: _withholding,
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(labelText: 'Retención (divisa)'),
                  ),
                  TextFormField(
                    controller: _currency,
                    decoration: const InputDecoration(labelText: 'Divisa'),
                    validator: (v) => (v ?? '').trim().length < 3
                        ? 'Divisa no válida'
                        : null,
                  ),
                ] else
                  TextFormField(
                    controller: _ratio,
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(
                      labelText: 'Ratio (2 = 2:1, 0.5 = 1:2)',
                    ),
                    validator: (v) => (_num(v ?? '') ?? 0) <= 0
                        ? 'Ratio debe ser mayor que 0'
                        : null,
                  ),
                TextFormField(
                  controller: _notes,
                  decoration: const InputDecoration(labelText: 'Notas (opcional)'),
                ),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancelar'),
        ),
        FilledButton(onPressed: _submit, child: const Text('Guardar')),
      ],
    );
  }
}
