import 'package:flutter/material.dart';

import '../models/indicators.dart';
import '../models/price_bar.dart';
import '../services/market_api.dart';
import '../widgets/candlestick_chart.dart';

/// Detalle de un activo: gráfico de velas + selector de intervalo.
class AssetDetailScreen extends StatefulWidget {
  const AssetDetailScreen({super.key, required this.symbol, required this.api});

  final String symbol;
  final MarketApi api;

  @override
  State<AssetDetailScreen> createState() => _AssetDetailScreenState();
}

class _AssetDetailScreenState extends State<AssetDetailScreen> {
  static const _intervals = ['1m', '5m', '1h', '1d'];

  String _interval = '1m';
  List<PriceBar> _bars = [];
  Indicators? _indicators;
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
      final bars = await widget.api.getBars(widget.symbol, interval: _interval);
      if (!mounted) return;
      setState(() {
        _bars = bars;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
    // Los indicadores son secundarios: si fallan, no rompen el gráfico.
    try {
      final indicators =
          await widget.api.getIndicators(widget.symbol, interval: _interval);
      if (!mounted) return;
      setState(() => _indicators = indicators);
    } catch (_) {
      if (!mounted) return;
      setState(() => _indicators = null);
    }
  }

  void _onIntervalChanged(String? value) {
    if (value == null || value == _interval) return;
    setState(() => _interval = value);
    _load();
  }

  Future<void> _openCreateAlert() async {
    final result = await showDialog<_AlertInput>(
      context: context,
      builder: (_) => const _CreateAlertDialog(),
    );
    if (result == null) return;
    try {
      await widget.api.createAlert(
        assetId: widget.symbol,
        type: result.type,
        direction: result.direction,
        threshold: result.threshold,
        indicator: result.indicator,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Alerta creada')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error creando alerta: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.symbol.toUpperCase()),
        actions: [
          IconButton(
            onPressed: _openCreateAlert,
            icon: const Icon(Icons.add_alert),
            tooltip: 'Crear alerta de precio',
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                const Text('Intervalo:'),
                const SizedBox(width: 12),
                DropdownButton<String>(
                  value: _interval,
                  items: _intervals
                      .map((i) => DropdownMenuItem(value: i, child: Text(i)))
                      .toList(),
                  onChanged: _onIntervalChanged,
                ),
                const Spacer(),
                IconButton(
                  onPressed: _load,
                  icon: const Icon(Icons.refresh),
                  tooltip: 'Refrescar',
                ),
              ],
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
    if (_bars.isEmpty) {
      return const Center(child: Text('Sin datos todavía'));
    }
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        SizedBox(height: 280, child: CandlestickChart(bars: _bars)),
        const SizedBox(height: 16),
        if (_indicators != null) _IndicatorsPanel(indicators: _indicators!),
      ],
    );
  }
}

/// Panel con el valor actual de los principales indicadores.
class _IndicatorsPanel extends StatelessWidget {
  const _IndicatorsPanel({required this.indicators});

  final Indicators indicators;

  String _fmt(double? v) => v == null ? '—' : v.toStringAsFixed(2);

  @override
  Widget build(BuildContext context) {
    final rsi = indicators.latest('rsi14');
    final rows = <(String, String)>[
      ('RSI (14)', _fmt(rsi)),
      ('SMA 20', _fmt(indicators.latest('sma20'))),
      ('SMA 50', _fmt(indicators.latest('sma50'))),
      ('EMA 20', _fmt(indicators.latest('ema20'))),
      ('MACD', _fmt(indicators.latest('macd'))),
      ('Señal MACD', _fmt(indicators.latest('macdSignal'))),
      ('ATR (14)', _fmt(indicators.latest('atr14'))),
      ('Bollinger sup.', _fmt(indicators.latest('bollingerUpper'))),
      ('Bollinger inf.', _fmt(indicators.latest('bollingerLower'))),
    ];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Indicadores', style: Theme.of(context).textTheme.titleMedium),
            if (rsi != null) _rsiHint(rsi),
            const SizedBox(height: 8),
            ...rows.map(
              (r) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(r.$1),
                    Text(r.$2, style: const TextStyle(fontWeight: FontWeight.w600)),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Pista textual del RSI (no solo color, por accesibilidad).
  Widget _rsiHint(double rsi) {
    String label;
    if (rsi >= 70) {
      label = 'Sobrecompra';
    } else if (rsi <= 30) {
      label = 'Sobreventa';
    } else {
      label = 'Neutral';
    }
    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Text('Estado RSI: $label', style: const TextStyle(fontSize: 12)),
    );
  }
}

/// Datos que devuelve el diálogo de creación de alerta.
class _AlertInput {
  const _AlertInput({
    required this.type,
    required this.direction,
    required this.threshold,
    this.indicator,
  });
  final String type;
  final String direction;
  final double threshold;
  final String? indicator;
}

class _CreateAlertDialog extends StatefulWidget {
  const _CreateAlertDialog();

  @override
  State<_CreateAlertDialog> createState() => _CreateAlertDialogState();
}

class _CreateAlertDialogState extends State<_CreateAlertDialog> {
  final _formKey = GlobalKey<FormState>();
  final _controller = TextEditingController();
  String _type = 'PRICE_CROSS';
  String _direction = 'ABOVE';
  String _indicator = 'rsi14';

  bool get _isIndicator => _type == 'INDICATOR_CROSS';
  bool get _isPercent => _type == 'PERCENT_CHANGE';

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  String get _thresholdLabel {
    if (_isPercent) return 'Variación umbral (%)';
    if (_isIndicator) return 'Valor umbral del indicador';
    return 'Precio umbral';
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    final value = double.parse(_controller.text.replaceAll(',', '.'));
    Navigator.of(context).pop(
      _AlertInput(
        type: _type,
        direction: _direction,
        threshold: value,
        indicator: _isIndicator ? _indicator : null,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Nueva alerta'),
      content: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<String>(
                initialValue: _type,
                decoration: const InputDecoration(labelText: 'Tipo de alerta'),
                items: const [
                  DropdownMenuItem(value: 'PRICE_CROSS', child: Text('Cruce de precio')),
                  DropdownMenuItem(value: 'PERCENT_CHANGE', child: Text('Variación %')),
                  DropdownMenuItem(value: 'INDICATOR_CROSS', child: Text('Cruce de indicador')),
                ],
                onChanged: (v) => setState(() => _type = v ?? 'PRICE_CROSS'),
              ),
              if (_isIndicator) ...[
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: _indicator,
                  decoration: const InputDecoration(labelText: 'Indicador'),
                  items: const [
                    DropdownMenuItem(value: 'rsi14', child: Text('RSI (14)')),
                    DropdownMenuItem(value: 'sma20', child: Text('SMA 20')),
                    DropdownMenuItem(value: 'ema20', child: Text('EMA 20')),
                  ],
                  onChanged: (v) => setState(() => _indicator = v ?? 'rsi14'),
                ),
              ],
              const SizedBox(height: 16),
              SegmentedButton<String>(
                segments: const [
                  ButtonSegment(value: 'ABOVE', label: Text('Por encima')),
                  ButtonSegment(value: 'BELOW', label: Text('Por debajo')),
                ],
                selected: {_direction},
                onSelectionChanged: (s) => setState(() => _direction = s.first),
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _controller,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                  signed: true,
                ),
                decoration: InputDecoration(labelText: _thresholdLabel),
                validator: (v) {
                  final parsed = double.tryParse((v ?? '').replaceAll(',', '.'));
                  if (parsed == null) {
                    return 'Introduce un número válido';
                  }
                  // Precio e indicador requieren > 0; la variación % admite negativos.
                  if (!_isPercent && parsed <= 0) {
                    return 'Debe ser mayor que 0';
                  }
                  return null;
                },
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
        FilledButton(onPressed: _submit, child: const Text('Crear')),
      ],
    );
  }
}
