import 'dart:async';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../core/config.dart';
import '../models/live_price.dart';
import '../services/live_stream.dart';
import '../services/market_api.dart';
import 'asset_detail_screen.dart';

/// Pantalla principal: watchlist con precios en vivo (polling REST en el MVP).
class WatchlistScreen extends StatefulWidget {
  const WatchlistScreen({super.key, required this.api});

  final MarketApi api;

  @override
  State<WatchlistScreen> createState() => _WatchlistScreenState();
}

class _WatchlistScreenState extends State<WatchlistScreen> {
  final _priceFormat = NumberFormat('#,##0.00');

  /// Precios indexados por símbolo (se actualizan en vivo por WebSocket).
  final Map<String, LivePrice> _prices = {};
  final LiveStream _liveStream = LiveStream();

  bool _loading = true;
  String? _error;
  Timer? _pollTimer;
  StreamSubscription<LivePrice>? _liveSub;

  @override
  void initState() {
    super.initState();
    _load();
    // Fuente principal: WebSocket. Actualiza los precios en tiempo real.
    _liveStream.connect();
    _liveSub = _liveStream.stream.listen((price) {
      if (!mounted) return;
      setState(() => _prices[price.symbol] = price);
    });
    // Respaldo: polling REST por si el WebSocket no está disponible.
    _pollTimer = Timer.periodic(AppConfig.livePollInterval, (_) => _load(silent: true));
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _liveSub?.cancel();
    _liveStream.dispose();
    super.dispose();
  }

  Future<void> _load({bool silent = false}) async {
    if (!silent) setState(() => _loading = true);
    try {
      final prices = await widget.api.getLivePrices();
      if (!mounted) return;
      setState(() {
        for (final p in prices) {
          _prices[p.symbol] = p;
        }
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

  Future<void> _openAddSymbol() async {
    final symbol = await showDialog<String>(
      context: context,
      builder: (_) => const _AddSymbolDialog(),
    );
    if (symbol == null || symbol.isEmpty) return;
    try {
      await widget.api.addToWatchlist(symbol);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${symbol.toUpperCase()} añadido a la watchlist')),
      );
      await _load(silent: true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error al añadir: $e')),
      );
    }
  }

  Future<void> _removeSymbol(String symbol) async {
    try {
      await widget.api.removeFromWatchlist(symbol);
      if (!mounted) return;
      setState(() => _prices.remove(symbol));
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${symbol.toUpperCase()} eliminado')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error al eliminar: $e')),
      );
      // Recarga para reflejar el estado real si falló.
      await _load(silent: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('MarketTracker'),
        actions: [
          IconButton(
            onPressed: () => _load(),
            icon: const Icon(Icons.refresh),
            tooltip: 'Refrescar',
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _openAddSymbol,
        tooltip: 'Añadir símbolo',
        child: const Icon(Icons.add),
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
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
              Text('No se pudo conectar con la API.\n$_error',
                  textAlign: TextAlign.center),
              const SizedBox(height: 12),
              FilledButton(onPressed: () => _load(), child: const Text('Reintentar')),
            ],
          ),
        ),
      );
    }
    if (_prices.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text(
            'La watchlist está vacía o sin datos aún.\nUsa el botón + para añadir un símbolo.',
            textAlign: TextAlign.center,
          ),
        ),
      );
    }
    final items = _prices.values.toList()
      ..sort((a, b) => a.symbol.compareTo(b.symbol));
    return RefreshIndicator(
      onRefresh: () => _load(),
      child: ListView.separated(
        itemCount: items.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (context, index) {
          final p = items[index];
          return Dismissible(
            key: ValueKey(p.symbol),
            direction: DismissDirection.endToStart,
            background: Container(
              color: Colors.red.shade400,
              alignment: Alignment.centerRight,
              padding: const EdgeInsets.only(right: 20),
              child: const Icon(Icons.delete, color: Colors.white),
            ),
            onDismissed: (_) => _removeSymbol(p.symbol),
            child: ListTile(
              title: Text(p.symbol.toUpperCase(),
                  style: const TextStyle(fontWeight: FontWeight.w600)),
              trailing: Text(
                _priceFormat.format(p.price),
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
              ),
              onTap: () => _openDetail(p.symbol),
            ),
          );
        },
      ),
    );
  }
}

/// Diálogo para añadir un símbolo a la watchlist.
class _AddSymbolDialog extends StatefulWidget {
  const _AddSymbolDialog();

  @override
  State<_AddSymbolDialog> createState() => _AddSymbolDialogState();
}

class _AddSymbolDialogState extends State<_AddSymbolDialog> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _submit() {
    final value = _controller.text.trim().toLowerCase();
    if (value.isEmpty) return;
    Navigator.of(context).pop(value);
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Añadir símbolo'),
      content: TextField(
        controller: _controller,
        autofocus: true,
        textInputAction: TextInputAction.done,
        onSubmitted: (_) => _submit(),
        decoration: const InputDecoration(
          labelText: 'Símbolo',
          hintText: 'p. ej. btcusdt',
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
