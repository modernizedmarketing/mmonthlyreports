# Mapa de Placeholders para el Deck Full Services

**Resumen**
- Usar el deck grande `FULL SERVICES Revision - Reporting Deck` como template amplio, tomando el template actual `Alpha Futures AI Report Template` como referencia validada.
- Agregar sólo placeholders que el pipeline actual puede llenar desde Hyros/Campaigns/Ads, overrides manuales e insights existentes.
- Verificación hecha: el template actual pasa `--audit-only` sin `missing_values`; el deck grande hoy no tiene placeholders.
- Regla manual: reemplazar el valor/texto visible por el placeholder en la misma caja/celda; no pegar el placeholder al final del texto existente.

**Mapa Seguro Para Agregar Ahora**
- Slides 1-4:
  - S1: `Name of the client` -> `{{CLIENT}}`; `July 2024` -> `{{REPORT_MONTH}}`.
  - S3: reemplazar las 3 cajas narrativas por `{{SLIDE3_GENERAL_INSIGHTS}}`, `{{SLIDE3_BUDGET_ROAS}}`, `{{SLIDE3_STRATEGY}}`.
  - S4: KPIs actuales -> `{{SLIDE4_AD_REVENUE}}`, `{{SLIDE4_AD_COST}}`, `{{SLIDE4_ROAS}}`, `{{SLIDE4_CPS}}`, `{{SLIDE4_L2S}}`, `{{SLIDE4_CVR}}`, `{{SLIDE4_AOV}}`; revenue company -> `{{COMPANY_REVENUE}}`; % ads -> `{{PCT_REV_FROM_ADS}}`; fila/valores last month -> tokens `_PREV`.
- Google Ads:
  - S6: valores bajo ROAS, Cost Per Sale, Lead To Sale, Conv. Rate, CTR -> `{{GOOGLE_ROAS}}`, `{{GOOGLE_CPS}}`, `{{GOOGLE_L2S}}`, `{{GOOGLE_CVR}}`, `{{GOOGLE_CTR}}`; si hay fila last month, usar tokens `{{GOOGLE_*_PREV}}`.
  - S8: top KPIs -> `{{GOOGLE_SALES}}`, `{{GOOGLE_LEADS}}`, `{{GOOGLE_CLICKS}}`, `{{GOOGLE_IMPRESSIONS}}`, `{{GOOGLE_L2S}}`, `{{GOOGLE_CVR}}`; dejar narrativas TOF/MOF/BOF manuales por ahora.
  - S9-S10: cards TOF/MOF/BOF -> `{{GOOGLE_TOF_REVENUE}}`, `{{GOOGLE_TOF_SALES}}`, `{{GOOGLE_TOF_ROAS}}`, `{{GOOGLE_TOF_CPS}}`, `{{GOOGLE_TOF_CR}}`, repitiendo patrón para `MOF` y `BOF`.
- Meta Ads:
  - S14: valores bajo ROAS, Cost Per Sale, Lead To Sale, Conv. Rate, CTR -> `{{META_ROAS}}`, `{{META_CPS}}`, `{{META_L2S}}`, `{{META_CVR}}`, `{{META_CTR}}`; si hay fila last month, usar `{{META_*_PREV}}`.
  - S16: top KPIs -> `{{META_SALES}}`, `{{META_LEADS}}`, `{{META_CLICKS}}`, `{{META_IMPRESSIONS}}`, `{{META_CTR}}`, `{{META_L2S}}`, `{{META_CVR}}`; dejar CPL/CPC manuales por ahora.
  - S17-S18: cards TOF/MOF/BOF -> mismo patrón `{{META_TOF_REVENUE}}`, `{{META_TOF_SALES}}`, `{{META_TOF_ROAS}}`, `{{META_TOF_CPS}}`, `{{META_TOF_CR}}`, etc.
- Bing Ads:
  - S22: valores bajo ROAS, Cost Per Sale, Lead To Sale, Conv. Rate, CTR -> `{{BING_ROAS}}`, `{{BING_CPS}}`, `{{BING_L2S}}`, `{{BING_CVR}}`, `{{BING_CTR}}`; si hay fila last month, usar `{{BING_*_PREV}}`.
  - S24/S25: top KPIs -> `{{BING_SALES}}`, `{{BING_LEADS}}`, `{{BING_CLICKS}}`, `{{BING_IMPRESSIONS}}`, `{{BING_CTR}}`, `{{BING_L2S}}`, `{{BING_CVR}}`; dejar CPL/CPC manuales por ahora.
  - S26-S27: cards TOF/MOF/BOF -> mismo patrón `{{BING_TOF_REVENUE}}`, `{{BING_TOF_SALES}}`, `{{BING_TOF_ROAS}}`, `{{BING_TOF_CPS}}`, `{{BING_TOF_CR}}`, etc.
- Narrativa general:
  - S42 `Insights From this Month`: puede usar `{{PM_NARRATIVE}}` si se quiere una slide resumen adicional.
  - S44 `Next Steps For Next Month`: usar `{{ACTION_ITEM_1}}` a `{{ACTION_ITEM_5}}` si se quiere separar next steps en bullets/cajas individuales.

**No Agregar Placeholders Todavía**
- S5, S7, S11-S12, S13, S15, S19-S20, S21, S23, S28-S29: servicios, scope of work o charts sin modelo automatizado actual.
- S30-S34: Twitter/X y TikTok Ads; el código actual sólo soporta Google, Meta y Bing/Microsoft.
- S35-S38: total ads performance, funnel distribution y comparaciones mensuales/trimestrales; requieren chart/data model nuevo.
- S39-S41: creatives y GEO insights; faltan fuentes estructuradas.
- S43: special request; hoy entra al prompt, pero no existe placeholder de slide separado.
- S45-S46: ClickCease y moderation; no hay fuente/modelo actual.
- S47-S68: social media orgánico/tablas/top posts/calendar; falta fuente estructurada.
- S69-S70: email marketing; falta fuente estructurada.
- S71: blank.

**Interfaz De Tokens**
- No usar los tokens del DOCX como `{{client_name}}` dentro de Slides; esos son variables del prompt, no placeholders del deck.
- Para el prompt `MM_Reporting_Prompt_v2`, mantener la salida conectada a los tres tokens existentes de S3: `{{SLIDE3_GENERAL_INSIGHTS}}`, `{{SLIDE3_BUDGET_ROAS}}`, `{{SLIDE3_STRATEGY}}`.
- Futuro opcional, con código antes de ponerlos en Slides: `{{*_TOF_NARRATIVE}}`, `{{*_MOF_NARRATIVE}}`, `{{*_BOF_NARRATIVE}}`, `{{*_CPL}}`, `{{*_CPC}}`, total funnel distribution, ClickCease, moderation, social, email y GEO.

**Test Plan**
- Después de que agregues placeholders manualmente al deck grande, correr `--audit-only`; debe salir `missing_values: []`.
- Generar una copia dry-run con un cliente de prueba y revisar que no queden placeholders ni valores sample viejos.
- Si se agregan tokens nuevos en código, actualizar `tools/report_replacements.py`, `build_audit_replacements`, tests de replacements y volver a correr `pytest`, `py_compile`, y `run_google_slides_report.py --help`.

**Supuestos**
- “Hybrids” se interpreta como el modelo actual de datos Hyros: tabs `Campaigns` y `Ads`.
- No se tocaron decks ni archivos en esta fase; esto es sólo el plan/mapa para edición manual.
- Cualquier slide con fuente no disponible queda manual hasta que compartas la nueva data source.
