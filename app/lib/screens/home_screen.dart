import 'package:flutter/material.dart';

import '../services/market_api.dart';
import 'dashboard_screen.dart';
import 'portfolio_screen.dart';
import 'watchlist_screen.dart';

/// Contenedor principal con navegación inferior entre Dashboard, Watchlist y Cartera.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.api, this.onLogout});

  final MarketApi api;

  /// Llamado cuando el usuario cierra sesión. Lo gestiona el gate de la app.
  final VoidCallback? onLogout;

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
        ],
      ),
    );
  }
}
