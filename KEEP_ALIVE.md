# Mantener Render Despierto (Keep-Alive)

Render en el plan gratuito **duerme el servicio después de 15 minutos** sin
tráfico. La primera visita después del sleep tarda ~30-60 segundos en
despertar. Esto NO se puede desactivar en el plan gratuito.

## 3 opciones para resolverlo

### Opción 1: UptimeRobot (GRATIS y RECOMENDADO)

Servicio externo que hace un ping cada 5 minutos a tu app, así nunca duerme.

**Pasos:**
1. Ve a **[uptimerobot.com](https://uptimerobot.com)** y crea cuenta gratis
2. Clic en **"Add New Monitor"**
3. Configura:
   - **Monitor Type:** HTTP(s)
   - **Friendly Name:** GestorRH Colombia
   - **URL:** `https://rh-facil.onrender.com`
   - **Monitoring Interval:** 5 minutes
4. Guarda

Con esto, Render nunca dormirá durante horas laborales.
**Límite gratuito:** 50 monitores, más que suficiente para 1 app.

---

### Opción 2: Cron-Job.org (alternativa gratis)

Similar a UptimeRobot pero permite programar horarios (útil si solo quieres
mantener despierto en horas laborales para ahorrar recursos).

1. **[cron-job.org](https://cron-job.org)** → crear cuenta
2. Add new cronjob
3. URL: `https://rh-facil.onrender.com`
4. Every 10 minutes, Mon-Fri, 07:00 - 22:00

---

### Opción 3: Upgrade a Render Starter ($7/mes)

Elimina el sleep automático completamente. Además incluye:
- 512MB RAM (vs 512MB en gratuito — igual)
- Sin auto-sleep
- Deploy más rápido
- Soporte por correo

Recomendado cuando tengas clientes pagando.

---

## Nota importante

El sleep de Render **no afecta la funcionalidad**, solo hace que la primera
carga sea lenta si no hay tráfico. Los datos siguen intactos en Supabase.

Con UptimeRobot configurado, tu app estará siempre disponible sin costo.
