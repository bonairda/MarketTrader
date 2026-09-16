import 'package:flutter/material.dart';

import '../services/market_api.dart';
import 'dashboard_screen.dart';
import 'watchlist_screen.dart';

/// Contenedor principal con navegación inferior entre Dashboard y Watchlist.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.api});

  final MarketApi api;

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
        appBar: AppBar(title: const Text('Mercado')),
        body: DashboardScreen(api: widget.api),
      ),
      WatchlistScreen(api: widget.api),
    ];

    return Scaffold(
      body: IndexedStack(index: _index, children: pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.dashboard), label: 'Mercado'),
          NavigationDestination(icon: Icon(Icons.star), label: 'Watchlist'),
        ],
      ),
    );
  }
}
