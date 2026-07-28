# 🎨 Carpeta de LOGO — Gestor RH IA

Esta es la carpeta donde va el logo de tu marca. La app lo usa automáticamente en:

- **Pantalla de login** — Logo grande centrado con tagline
- **Sidebar** — Logo pequeño arriba a la izquierda cuando estás dentro
- **Favicon** — Ícono en la pestaña del navegador

---

## 📁 Archivos que van aquí

### 1. `logo_gestorrh.png` (OBLIGATORIO)

**El logo principal completo — con texto "Gestor RH IA".**

- Se usa en la pantalla de login (grande) y en el sidebar (redimensionado)
- **Tamaño recomendado:** 1200x400 píxeles o superior
- **Formato:** PNG con fondo transparente
- **Peso:** menos de 500 KB

### 2. `logo_icono.png` (OPCIONAL)

**Solo el ícono cuadrado, sin texto.**

- Se usa como favicon del navegador
- **Tamaño recomendado:** 400x400 píxeles o superior (cuadrado)
- **Formato:** PNG con fondo transparente
- Si no lo subes, se usa `logo_gestorrh.png` como fallback

---

## 🔄 Cómo reemplazar el logo

Actualmente esta carpeta contiene un **placeholder generado por Claude** (no es el logo profesional real). Puedes reemplazarlo así:

### Opción A — GitHub Web (más fácil)

1. Ve a `https://github.com/thatan2001-debug/gestorh/tree/main/assets`
2. Clic sobre `logo_gestorrh.png` (el archivo)
3. Botón **"Edit"** (ícono lápiz arriba a la derecha) → si no aparece, ve a **"Delete this file"** y luego sube el nuevo
4. Alternativamente: **Add file → Upload files**
5. Arrastra tu logo (debe llamarse exactamente `logo_gestorrh.png`)
6. **Commit changes**

En 2-3 minutos Render redesplegará y verás tu logo real.

### Opción B — Sobrescribir localmente y hacer push

```bash
# En tu computador, en la carpeta del repo
cp /ruta/a/tu/logo.png assets/logo_gestorrh.png

git add assets/logo_gestorrh.png
git commit -m "feat: nuevo logo real de la marca"
git push
```

---

## ⚠️ Reglas importantes

- **El nombre debe ser EXACTO:** `logo_gestorrh.png` (todo en minúsculas, con guion bajo)
- **Formato PNG obligatorio** — no JPG (los JPG no soportan fondo transparente)
- **Fondo transparente:** si tu logo tiene fondo blanco, se verá una caja blanca fea en el sidebar
- **No borres esta carpeta** — la app la busca. Si el archivo no existe, la app usa un emoji 📄 como fallback y no se rompe

---

## 🧪 Cómo verificar que funcionó

Después de subir tu logo:

1. Espera 2-3 minutos a que Render redesplegue
2. Abre tu app en una ventana de incógnito (para evitar caché)
3. En la pantalla de login **debe aparecer tu logo** en vez del emoji
4. Al ingresar, en el sidebar (arriba a la izquierda) **también debe aparecer**
5. En la pestaña del navegador **debe estar el favicon** con tu logo

Si NO se ve:
- Verifica que el archivo se llame exactamente `logo_gestorrh.png`
- Verifica en GitHub que el archivo está dentro de `assets/`
- Fuerza rebuild en Render: Dashboard → tu servicio → Manual Deploy

---

## 💡 Recomendaciones si necesitas hacer el logo profesional

Si aún no tienes el archivo real del logo profesional (el diseño que viste en la referencia), te doy 3 caminos:

- **Canva** ($0-6/mes): plantillas de "Tech Logo" o "SaaS Logo", editable en 30 min
- **Fiverr** (USD $30-50): busca "logo tech Colombia" y pásale la referencia visual
- **Diseñador local** (COP $150k-500k): agencia de diseño en Medellín o Bogotá

Como estás en fase beta, el placeholder actual sirve mientras validas con usuarios. Cuando ya haya feedback positivo, invierte en el logo profesional.
