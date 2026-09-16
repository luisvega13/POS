# POS local para impresora térmica de 58 mm

Sistema de punto de venta para Windows con frontend React + TypeScript, catálogo, carrito, cobro, historial, caja y tickets térmicos. La impresión conserva el flujo probado: navegador → FastAPI → `TicketBuilder` → `pywin32` → spooler de Windows → impresora USB.

Una venta se confirma primero en una transacción SQLite. La impresión ocurre después: si falla, la venta permanece registrada y puede reimprimirse desde el historial.

## Instalación

Requiere Python 3.10+ y el driver de la impresora instalado en Windows.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Para ejecutar las pruebas:

```powershell
pip install pytest
pytest -q
```

## Inicio

```powershell
python -m app.main
```

Abra [http://localhost:8000](http://localhost:8000). El servidor escucha únicamente en `127.0.0.1` de forma predeterminada.

## Desarrollo del frontend

El frontend está en `frontend/` y utiliza React, TypeScript y Vite:

```powershell
cd frontend
pnpm install
pnpm dev
```

Vite abre `http://127.0.0.1:5173` y redirige `/api` al backend local. Para generar la versión de producción que sirve FastAPI:

```powershell
pnpm build
```

El resultado se guarda en `frontend/dist/`. FastAPI sirve ese build y ya no depende de las plantillas y scripts anteriores.

En el primer arranque se crea `data/pos.db` y sus tablas. Para esta primera etapa el esquema se administra con `SQLAlchemy.metadata.create_all()`. Antes de distribuir actualizaciones que alteren tablas existentes debe incorporarse Alembic; `create_all` no reemplaza migraciones de producción.

## Flujo operativo

### Cargar productos

Use **Productos → Nuevo producto**, o cargue los cuatro ejemplos opcionales:

```powershell
python -m scripts.seed_demo
```

El script es idempotente por nombre y nunca se ejecuta automáticamente.

Las categorías se administran desde **Productos → Categorías**. Pueden crearse y renombrarse; al renombrar se actualizan los productos relacionados. Una categoría con productos no puede eliminarse hasta reasignarlos.

### Configurar negocio e impresora

En **Configuración** indique nombre, dirección, teléfono, mensaje final, impresora, encoding y tabla de caracteres. La selección se sincroniza con el servicio RAW existente. Si los acentos no coinciden, use **Diagnosticar caracteres** y seleccione la tabla cuya línea sea correcta.

### Abrir caja

Entre a **Corte de caja**, pulse **Abrir caja** e indique el fondo inicial. No se permiten ventas sin una sesión abierta.

### Realizar una venta

1. En **Punto de venta**, busque o filtre productos y pulse sus tarjetas.
2. Ajuste cantidades en el carrito.
3. Pulse **Cobrar**.
4. Seleccione efectivo, tarjeta o transferencia.
5. Para efectivo, capture el importe recibido; el sistema valida el pago y calcula el cambio.
6. Confirme. El backend vuelve a consultar productos y precios, guarda venta e items en una transacción y después envía el ticket.

Los importes usan `Decimal` y columnas SQL `NUMERIC(12,2)`, nunca `float` para cálculos financieros. `SaleItem` conserva nombre y precio histórico aunque el producto cambie después.

### Historial y reimpresión

En **Ventas**, abra una operación para consultar artículos, cantidades, total y método. **Reimprimir ticket** utiliza el registro existente y no crea otra venta.

En esa misma sección, **Productos vendidos** muestra cuántas unidades se vendieron, cuáles productos fueron, en cuántas operaciones aparecieron y el importe acumulado. Puede filtrarse por fecha; los cálculos proceden de `sale_items` en el backend.

### Corte de caja

**Corte de caja** muestra apertura, fondo, operaciones, ventas por método, total vendido y efectivo esperado (`fondo inicial + ventas en efectivo`). Todos los valores se calculan desde SQLite. Puede imprimir el corte y cerrarlo; antes del cierre se presenta el resumen y se solicita confirmación.

## API principal

Productos:

- `GET/POST /api/products`
- `GET/PUT/DELETE /api/products/{id}`
- `GET /api/products/categories`

Ventas:

- `GET/POST /api/sales`
- `GET /api/sales/{id}`
- `POST /api/sales/{id}/print`

Caja:

- `GET /api/cash/current`
- `POST /api/cash/open`
- `GET /api/cash/summary`
- `POST /api/cash/print`
- `POST /api/cash/close`

Configuración e impresión:

- `GET/PUT /api/config`
- `GET /api/printers`
- Se mantienen los endpoints de prueba RAW bajo `/api/print/*`.

La documentación interactiva está en [http://localhost:8000/docs](http://localhost:8000/docs).

## Despliegue en Windows

El POS debe ejecutarse en la computadora Windows conectada físicamente a la impresora. Para instalar o actualizar dependencias y preparar SQLite:

```powershell
powershell -ExecutionPolicy Bypass -File deploy\install_windows.ps1
```

Inicio de producción, sin recarga de desarrollo:

```powershell
powershell -ExecutionPolicy Bypass -File deploy\run_pos.ps1
```

Para registrar el inicio automático al iniciar sesión en Windows:

```powershell
powershell -ExecutionPolicy Bypass -File deploy\install_windows.ps1 -RegisterStartup
```

El servicio escucha en `127.0.0.1:8000`; no expone ventas, caja ni impresora a la red local. Para respaldar la base:

```powershell
powershell -ExecutionPolicy Bypass -File deploy\backup_pos.ps1
```

## Estructura

```text
app/
  api/
    pos_routes.py
    printer_routes.py
  printer/
    commands.py
    printer_service.py
    ticket_builder.py
  services/
    config_service.py
    pos_service.py
    ticket_service.py
  static/
    css/styles.css
    js/pos.js
  templates/index.html
  database.py
  models.py
  main.py
data/pos.db
scripts/seed_demo.py
tests/
```

## Pruebas y seguridad de datos

La suite cubre CRUD de productos, validaciones, ventas de efectivo/tarjeta/transferencia, cambio, múltiples productos, folios, snapshots históricos, resumen y cierre de caja, efectivo esperado, tickets de 32 columnas y el servicio de impresión previamente existente.

Los logs están en `logs/app.log` y no almacenan el contenido completo de tickets. Realice respaldos periódicos de `data/pos.db`; contiene ventas y sesiones de caja.

La confirmación de impresión solo significa que Windows aceptó el trabajo en el spooler, no que el papel salió físicamente.
