import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../services/market_api.dart';

/// Ajustes de notificaciones: vinculación del chat de Telegram por usuario.
///
/// El usuario pide un código, lo envía al bot con `/start <código>` y el backend
/// vincula su chat. A partir de ahí, sus alertas le llegan solo a él.
class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key, required this.api});

  final MarketApi api;

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  bool _loading = true;
  bool _busy = false;
  String? _error;

  bool _botConfigured = false;
  bool _linked = false;
  bool _enabled = false;

  String? _code;
  String? _instructions;
  int? _expiresInSeconds;

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
      final status = await widget.api.getTelegramStatus();
      if (!mounted) return;
      setState(() {
        _botConfigured = status['botConfigured'] == true;
        _linked = status['linked'] == true;
        _enabled = status['enabled'] == true;
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

  Future<void> _generateCode() async {
    setState(() => _busy = true);
    try {
      final result = await widget.api.createTelegramLinkCode();
      if (!mounted) return;
      if (result['botConfigured'] != true) {
        setState(() {
          _botConfigured = false;
          _busy = false;
        });
        return;
      }
      setState(() {
        _code = result['code'] as String?;
        _instructions = result['instructions'] as String?;
        _expiresInSeconds = result['expiresInSeconds'] as int?;
        _busy = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _busy = false);
      _snack('No se pudo generar el código: $e');
    }
  }

  Future<void> _copyCode() async {
    final code = _code;
    if (code == null) return;
    await Clipboard.setData(ClipboardData(text: '/start $code'));
    _snack('Comando copiado. Pégalo en el chat del bot.');
  }

  Future<void> _toggleEnabled(bool value) async {
    setState(() => _busy = true);
    try {
      await widget.api.setTelegramEnabled(value);
      if (!mounted) return;
      setState(() {
        _enabled = value;
        _busy = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _busy = false);
      _snack('No se pudo actualizar: $e');
    }
  }

  Future<void> _unlink() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Desvincular Telegram'),
        content: const Text(
          'Dejarás de recibir tus alertas en Telegram. ¿Continuar?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Desvincular'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    setState(() => _busy = true);
    try {
      await widget.api.unlinkTelegram();
      if (!mounted) return;
      setState(() {
        _linked = false;
        _enabled = false;
        _code = null;
        _instructions = null;
        _busy = false;
      });
      _snack('Telegram desvinculado.');
    } catch (e) {
      if (!mounted) return;
      setState(() => _busy = false);
      _snack('No se pudo desvincular: $e');
    }
  }

  void _snack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Notificaciones')),
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
              Text('No se pudo cargar el estado.\n$_error',
                  textAlign: TextAlign.center),
              const SizedBox(height: 12),
              FilledButton(onPressed: _load, child: const Text('Reintentar')),
            ],
          ),
        ),
      );
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.send, size: 22),
                    const SizedBox(width: 10),
                    Text('Telegram',
                        style: Theme.of(context).textTheme.titleMedium),
                  ],
                ),
                const SizedBox(height: 8),
                const Text(
                  'Vincula tu chat de Telegram para recibir tus alertas de precio '
                  'e indicadores. Solo tú las recibes.',
                  style: TextStyle(fontSize: 13),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        if (!_botConfigured)
          const Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Text(
                'El administrador no ha configurado el bot de Telegram, así que '
                'la vinculación no está disponible por ahora.',
                style: TextStyle(fontSize: 13),
              ),
            ),
          )
        else if (_linked)
          _linkedCard()
        else
          _linkFlowCard(),
      ],
    );
  }

  Widget _linkedCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.check_circle,
                    color: Colors.green.shade700, size: 22),
                const SizedBox(width: 10),
                const Expanded(
                  child: Text('Chat vinculado',
                      style: TextStyle(fontWeight: FontWeight.w600)),
                ),
              ],
            ),
            const SizedBox(height: 8),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Recibir alertas en Telegram'),
              value: _enabled,
              onChanged: _busy ? null : _toggleEnabled,
            ),
            const SizedBox(height: 4),
            Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: _busy ? null : _unlink,
                icon: const Icon(Icons.link_off),
                label: const Text('Desvincular'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _linkFlowCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Cómo vincular:',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            const Text('1. Genera un código.\n'
                '2. Abre el bot de Telegram del proyecto.\n'
                '3. Envía el comando /start con tu código.'),
            const SizedBox(height: 16),
            if (_code != null) ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SelectableText(
                      '/start $_code',
                      style: const TextStyle(
                        fontFamily: 'monospace',
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    if (_expiresInSeconds != null) ...[
                      const SizedBox(height: 6),
                      Text(
                        'Caduca en ${(_expiresInSeconds! / 60).round()} min.',
                        style: const TextStyle(fontSize: 12),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 8),
              if (_instructions != null)
                Text(_instructions!, style: const TextStyle(fontSize: 12)),
              const SizedBox(height: 12),
              Row(
                children: [
                  OutlinedButton.icon(
                    onPressed: _copyCode,
                    icon: const Icon(Icons.copy),
                    label: const Text('Copiar comando'),
                  ),
                  const SizedBox(width: 8),
                  TextButton(
                    onPressed: _busy ? null : _load,
                    child: const Text('Ya lo he enviado'),
                  ),
                ],
              ),
            ] else
              FilledButton.icon(
                onPressed: _busy ? null : _generateCode,
                icon: _busy
                    ? const SizedBox(
                        height: 18,
                        width: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.vpn_key),
                label: const Text('Generar código'),
              ),
          ],
        ),
      ),
    );
  }
}
