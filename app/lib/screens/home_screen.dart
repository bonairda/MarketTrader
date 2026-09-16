import 'package:flutter/material.dart';

import '../services/market_api.dart';
import 'admin_screen.dart';
import 'dashboard_screen.dart';
import 'operations_screen.dart';
import 'portfolio_screen.dart';
import 'watchlist_screen.dart';

/// Navegación principal: mercado, watchlist, cartera y libro de operaciones.
class HomeScreen extends StatefulWidget {
  const HomeScreen({
    super.key,
    required this.api,
    this.onLogout,
    this.isSuperadmin = false,
  });

  final MarketApi api;

  /// Llamado cuando el usuario cierra sesión. Lo gestiona el gate de la app.
  final VoidCallback? onLogout;

  /// Muestra el acceso al panel de administración si el usuario es SUPERADMIN.
  final bool isSuperadmin;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    // La WatchlistScreen ya es un Scaffold completo (AppBar + FAB). El Dashboard
    // devuelve solo el body, así que aquí le damos su propio AppBar.
    final pages = [
      Scaffold(
        appBar: AppBar(
          title: const Text('Mercado'),
          actions: [
            if (widget.isSuperadmin)
              IconButton(
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => AdminScreen(api: widget.api),
                  ),
                ),
                icon: const Icon(Icons.admin_panel_settings),
                tooltip: 'Administración',
              ),
            if (widget.onLogout != null)
              IconButton(
                onPressed: widget.onLogout,
                icon: const Icon(Icons.logout),
                tooltip: 'Cerrar sesión',
              ),
          ],
        ),
        body: DashboardScreen(api: widget.api),
      ),
      WatchlistScreen(api: widget.api),
      PortfolioScreen(api: widget.api),
      OperationsScreen(api: widget.api),
    ];

    return Scaffold(
      body: IndexedStack(index: _index, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.dashboard), label: 'Mercado'),
          NavigationDestination(icon: Icon(Icons.star), label: 'Watchlist'),
          NavigationDestination(
              icon: Icon(Icons.account_balance_wallet), label: 'Cartera'),
          NavigationDestination(
              icon: Icon(Icons.swap_horiz), label: 'Operaciones'),
        ],
      ),
    );
  }
}
