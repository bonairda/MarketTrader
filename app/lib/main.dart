import 'package:flutter/material.dart';

import 'core/config.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'services/auth_service.dart';
import 'services/market_api.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await AppConfig.initialize();
  runApp(const MarketTrackerApp());
}

class MarketTrackerApp extends StatefulWidget {
  const MarketTrackerApp({super.key});

  @override
  State<MarketTrackerApp> createState() => _MarketTrackerAppState();
}

class _MarketTrackerAppState extends State<MarketTrackerApp> {
  final MarketApi _api = MarketApi();
  late final AuthService _auth = AuthService(api: _api);

  @override
  void dispose() {
    _api.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MarketTracker',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF1E88E5),
        useMaterial3: true,
      ),
      home: _AuthGate(api: _api, auth: _auth),
    );
  }
}

/// Decide qué pantalla mostrar según el estado de sesión:
/// - Mientras comprueba el token guardado: splash.
/// - Sin sesión válida: LoginScreen.
/// - Con sesión válida: HomeScreen.
class _AuthGate extends StatefulWidget {
  const _AuthGate({required this.api, required this.auth});

  final MarketApi api;
  final AuthService auth;

  @override
  State<_AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<_AuthGate> {
  bool _checking = true;
  bool _authenticated = false;

  @override
  void initState() {
    super.initState();
    widget.api.onUnauthorized = _handleUnauthorized;
    _restore();
  }

  @override
  void dispose() {
    widget.api.onUnauthorized = null;
    super.dispose();
  }

  void _handleUnauthorized() {
    widget.auth.logout().ignore();
    if (!mounted) return;
    setState(() {
      _authenticated = false;
      _checking = false;
    });
  }

  Future<void> _restore() async {
    final hadSession = await widget.auth.loadSession();
    // Si había token, comprobamos contra el backend que sigue siendo válido.
    final valid = hadSession && await widget.auth.validateSession();
    if (!mounted) return;
    setState(() {
      _authenticated = valid;
      _checking = false;
    });
  }

  void _onAuthenticated() => setState(() => _authenticated = true);

  Future<void> _onLogout() async {
    await widget.auth.logout();
    if (!mounted) return;
    setState(() => _authenticated = false);
  }

  @override
  Widget build(BuildContext context) {
    if (_checking) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (!_authenticated) {
      return LoginScreen(auth: widget.auth, onAuthenticated: _onAuthenticated);
    }
    return HomeScreen(
      api: widget.api,
      onLogout: _onLogout,
      isSuperadmin: widget.auth.isSuperadmin,
    );
  }
}
