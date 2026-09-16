import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/tax_report.dart';
import '../services/market_api.dart';

/// Informe fiscal anual FIFO. El CSV se copia al portapapeles para que funcione
/// igual en web, escritorio y móvil sin plugins nativos adicionales.
class TaxReportScreen extends StatefulWidget {
  const TaxReportScreen({super.key, required this.api});

  final MarketApi api;

  @override
  State<TaxReportScreen> createState() => _TaxReportScreenState();
}

class _TaxReportScreenState extends State<TaxReportScreen> {
  int _year = DateTime.now().year;
  TaxReport? _report;
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
      final report = await widget.api.getTaxReport(_year);
      if (!mounted) return;
      setState(() {
        _report = report;
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

  Future<void> _copyCsv() async {
    try {
      final csv = await widget.api.getTaxCsv(_year);
      await Clipboard.setData(ClipboardData(text: csv));
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('CSV copiado al portapapeles')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No se pudo obtener el CSV: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Informe fiscal FIFO'),
        actions: [
          IconButton(
            onPressed: _report == null ? null : _copyCsv,
            icon: const Icon(Icons.file_copy_outlined),
            tooltip: 'Copiar CSV',
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                const Text('Ejercicio:'),
                const SizedBox(width: 12),
                DropdownButton<int>(
                  value: _year,
                  items: List.generate(8, (i) => DateTime.now().year - i)
                      .map((year) => DropdownMenuItem(value: year, child: Text('$year')))
                      .toList(),
                  onChanged: (year) {
                    if (year == null) return;
                    setState(() => _year = year);
                    _load();
                  },
                ),
                const Spacer(),
                IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
              ],
            ),
          ),
          Expanded(child: _body()),
        ],
      ),
    );
  }

  Widget _body() {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) return Center(child: Text('Error: $_error'));
    final report = _report!;
    final gain = double.tryParse(report.summary.realizedGainEur) ?? 0;
    final gainColor = gain >= 0 ? Colors.green.shade700 : Colors.red.shade700;
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Resumen ${report.year}',
                    style: Theme.of(context).textTheme.titleMedium),
                _row('Ventas', '${report.summary.sellOperations}'),
                _row('Lotes FIFO', '${report.summary.matchedLots}'),
                _row('Valor transmisión', '${report.summary.proceedsEur} EUR'),
                _row('Valor adquisición', '${report.summary.acquisitionCostEur} EUR'),
                _row('Comisiones asignadas', '${report.summary.feesEur} EUR'),
                _row(
                  'Ganancia / pérdida',
                  '${gain >= 0 ? '+' : ''}${report.summary.realizedGainEur} EUR',
                  color: gainColor,
                ),
              ],
            ),
          ),
        ),
        if (report.summary.washSaleDisposals > 0)
          Card(
            color: Colors.amber.shade100,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.warning_amber, color: Colors.amber.shade900),
                      const SizedBox(width: 8),
                      const Expanded(
                        child: Text(
                          'Posible recompra de valores homogéneos',
                          style: TextStyle(fontWeight: FontWeight.bold),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '${report.summary.washSaleDisposals} pérdida(s) por '
                    '${report.summary.washSaleAdjustmentEur} EUR podrían no ser '
                    'computables este ejercicio por la regla AEAT de valores '
                    'homogéneos (±2 meses). Revísalo con tu asesor.',
                    style: const TextStyle(fontSize: 12),
                  ),
                ],
              ),
            ),
          ),
        if (report.dividends != null && report.dividends!.count > 0)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Dividendos ${report.year}',
                      style: Theme.of(context).textTheme.titleMedium),
                  _row('Nº de dividendos', '${report.dividends!.count}'),
                  _row('Bruto', '${report.dividends!.grossEur} EUR'),
                  _row('Retención', '${report.dividends!.withholdingEur} EUR'),
                  _row('Neto', '${report.dividends!.netEur} EUR'),
                ],
              ),
            ),
          ),
        const SizedBox(height: 8),
        Text('Por activo', style: Theme.of(context).textTheme.titleMedium),
        if (report.assets.isEmpty)
          const Padding(
            padding: EdgeInsets.all(16),
            child: Text('No hay ventas realizadas en este ejercicio.'),
          ),
        ...report.assets.map((asset) {
          final assetGain = double.tryParse(asset.realizedGainEur) ?? 0;
          return Card(
            child: ListTile(
              title: Text(asset.assetId.toUpperCase()),
              subtitle: Text(
                '${asset.quantitySold} uds. · transmisión ${asset.proceedsEur} EUR',
              ),
              trailing: Text(
                '${assetGain >= 0 ? '+' : ''}${asset.realizedGainEur} EUR',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: assetGain >= 0 ? Colors.green.shade700 : Colors.red.shade700,
                ),
              ),
            ),
          );
        }),
        const SizedBox(height: 8),
        Text('Emparejamientos FIFO', style: Theme.of(context).textTheme.titleMedium),
        ...report.disposals.map(
          (row) => Card(
            child: ListTile(
              leading: row.washSale
                  ? Icon(Icons.warning_amber, color: Colors.amber.shade900)
                  : null,
              title: Text('${row.assetId.toUpperCase()} · ${row.matchedQuantity}'),
              subtitle: Text(
                'Compra ${row.acquisitionDate} → venta ${row.saleDate}\n'
                'Adquisición ${row.acquisitionCostEur} · transmisión ${row.proceedsEur} EUR'
                '${row.washSale ? '\nPosible recompra homogénea: pérdida no computable' : ''}',
              ),
              isThreeLine: row.washSale,
              trailing: Text('${row.gainEur} EUR'),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 16),
          child: Text(
            report.disclaimer,
            style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic),
          ),
        ),
      ],
    );
  }

  Widget _row(String label, String value, {Color? color}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label),
            Text(value, style: TextStyle(fontWeight: FontWeight.w600, color: color)),
          ],
        ),
      );
}
