import 'package:flutter/material.dart';

import '../services/market_api.dart';

/// Panel de administración de usuarios. Solo accesible para SUPERADMIN.
///
/// Permite listar usuarios, crear nuevos con rol, cambiar el rol, activar/
/// desactivar y borrar. Las salvaguardas (no auto-degradarse/borrarse) las aplica
/// el backend; aquí solo se muestran los errores que devuelva.
class AdminScreen extends StatefulWidget {
  const AdminScreen({super.key, required this.api});

  final MarketApi api;

  @override
  State<AdminScreen> createState() => _AdminScreenState();
}

class _AdminScreenState extends State<AdminScreen> {
  static const _roles = ['SUPERADMIN', 'OWNER', 'VIEWER'];

  List<Map<String, dynamic>> _users = [];
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
      final users = await widget.api.adminListUsers();
      if (!mounted) return;
      setState(() {
        _users = users;
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

  void _snack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _createUser() async {
    final created = await showDialog<bool>(
      context: context,
      builder: (_) => _CreateUserDialog(api: widget.api),
    );
    if (created == true) await _load();
  }

  Future<void> _changeRole(Map<String, dynamic> user) async {
    final current = user['role'] as String? ?? 'OWNER';
    final role = await showDialog<String>(
      context: context,
      builder: (_) => _RolePickerDialog(current: current, roles: _roles),
    );
    if (role == null || role == current) return;
    try {
      await widget.api.adminSetRole(user['id'] as String, role);
      _snack('Rol actualizado a $role');
      await _load();
    } catch (e) {
      _snack('No se pudo cambiar el rol: $e');
    }
  }

  Future<void> _toggleActive(Map<String, dynamic> user) async {
    final active = user['isActive'] == true;
    try {
      await widget.api.adminSetActive(user['id'] as String, !active);
      _snack(active ? 'Usuario desactivado' : 'Usuario activado');
      await _load();
    } catch (e) {
      _snack('No se pudo actualizar: $e');
    }
  }

  Future<void> _deleteUser(Map<String, dynamic> user) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Borrar usuario'),
        content: Text('¿Borrar a ${user['email']}? Esta acción no se puede deshacer.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Borrar'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await widget.api.adminDeleteUser(user['id'] as String);
      _snack('Usuario borrado');
      await _load();
    } catch (e) {
      _snack('No se pudo borrar: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Administración'),
        actions: [
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _createUser,
        icon: const Icon(Icons.person_add),
        label: const Text('Nuevo usuario'),
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
              const Icon(Icons.lock, size: 48),
              const SizedBox(height: 12),
              Text('No se pudo cargar el panel.\n$_error',
                  textAlign: TextAlign.center),
              const SizedBox(height: 12),
              FilledButton(onPressed: _load, child: const Text('Reintentar')),
            ],
          ),
        ),
      );
    }
    if (_users.isEmpty) {
      return const Center(child: Text('No hay usuarios.'));
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.separated(
        itemCount: _users.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (context, index) {
          final u = _users[index];
          final active = u['isActive'] == true;
          return ListTile(
            leading: CircleAvatar(
              child: Icon(active ? Icons.person : Icons.person_off),
            ),
            title: Text(u['email'] as String? ?? '—'),
            subtitle: Text('${u['role']} · ${active ? 'activo' : 'inactivo'}'),
            trailing: PopupMenuButton<String>(
              onSelected: (value) {
                switch (value) {
                  case 'role':
                    _changeRole(u);
                  case 'active':
                    _toggleActive(u);
                  case 'delete':
                    _deleteUser(u);
                }
              },
              itemBuilder: (_) => [
                const PopupMenuItem(value: 'role', child: Text('Cambiar rol')),
                PopupMenuItem(
                  value: 'active',
                  child: Text(active ? 'Desactivar' : 'Activar'),
                ),
                const PopupMenuItem(value: 'delete', child: Text('Borrar')),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _RolePickerDialog extends StatelessWidget {
  const _RolePickerDialog({required this.current, required this.roles});

  final String current;
  final List<String> roles;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Cambiar rol'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: roles
            .map((r) => RadioListTile<String>(
                  title: Text(r),
                  value: r,
                  groupValue: current,
                  onChanged: (v) => Navigator.of(context).pop(v),
                ))
            .toList(),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancelar'),
        ),
      ],
    );
  }
}

class _CreateUserDialog extends StatefulWidget {
  const _CreateUserDialog({required this.api});

  final MarketApi api;

  @override
  State<_CreateUserDialog> createState() => _CreateUserDialogState();
}

class _CreateUserDialogState extends State<_CreateUserDialog> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  String _role = 'OWNER';
  bool _busy = false;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      await widget.api.adminCreateUser(
        email: _emailController.text.trim(),
        password: _passwordController.text,
        role: _role,
      );
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } catch (e) {
      if (!mounted) return;
      setState(() => _busy = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('No se pudo crear: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Nuevo usuario'),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextFormField(
              controller: _emailController,
              keyboardType: TextInputType.emailAddress,
              decoration: const InputDecoration(labelText: 'Email'),
              validator: (v) {
                final value = (v ?? '').trim();
                if (value.isEmpty || !value.contains('@')) {
                  return 'Introduce un email válido';
                }
                return null;
              },
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _passwordController,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'Contraseña'),
              validator: (v) =>
                  (v ?? '').length < 8 ? 'Mínimo 8 caracteres' : null,
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: _role,
              decoration: const InputDecoration(labelText: 'Rol'),
              items: const [
                DropdownMenuItem(value: 'OWNER', child: Text('OWNER')),
                DropdownMenuItem(value: 'VIEWER', child: Text('VIEWER')),
                DropdownMenuItem(value: 'SUPERADMIN', child: Text('SUPERADMIN')),
              ],
              onChanged: (v) => setState(() => _role = v ?? 'OWNER'),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _busy ? null : () => Navigator.of(context).pop(false),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          onPressed: _busy ? null : _submit,
          child: _busy
              ? const SizedBox(
                  height: 18,
                  width: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Text('Crear'),
        ),
      ],
    );
  }
}
