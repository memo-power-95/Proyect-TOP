let intervaloActualizacion;
const INTERVALO_REFRESH = 2000;
const charts = {};

document.addEventListener("DOMContentLoaded", async () => {
    await actualizarEstado();
    await cargarMaquinasLineaVivo();
    await cargarDashboardVivo();
    const lineSel = document.getElementById("vivo-linea");
    if (lineSel) {
        lineSel.addEventListener("change", async () => {
            await cargarMaquinasLineaVivo();
            await cargarDashboardVivo();
        });
    }
    // Solo actualizar dashboard vivo automáticamente
    intervaloActualizacion = setInterval(actualizarVivo, INTERVALO_REFRESH);
});

async function cargarMaquinasLineaVivo() {
    const linea = document.getElementById("vivo-linea")?.value || "1";
    const sel = document.getElementById("vivo-maquina");
    if (!sel) return;

    try {
        const response = await fetch(`/api/maquinas?linea=${encodeURIComponent(linea)}`);
        const data = await response.json();
        const maquinas = data.maquinas || [];
        sel.innerHTML = '<option value="ALL">Todas</option>';
        maquinas.forEach((m) => {
            const op = document.createElement("option");
            op.value = m;
            op.textContent = m;
            sel.appendChild(op);
        });
    } catch (error) {
        sel.innerHTML = '<option value="ALL">Todas</option>';
    }
}

async function actualizarVivo() {
    await cargarDashboardVivo();
}

async function actualizarEstado() {
    try {
        const responseModulos = await fetch("/api/modulos");
        const modulos = await responseModulos.json();

        const responseEstado = await fetch("/api/estado");
        const estado = await responseEstado.json();

        actualizarModulos(modulos);
        actualizarInfoSistema(estado);
        actualizarTablaProcesos(estado.procesos);
        document.getElementById("ultima-actualizacion").textContent = new Date().toLocaleTimeString();
    } catch (error) {
        mostrarNotificacion("Error", "No se pudo actualizar el estado general", "error");
    }
}

function actualizarModulos(modulos) {
    modulos.forEach((modulo) => {
        const estadoBadge = document.getElementById(`estado-${modulo.id}`);
        const btnIniciar = document.getElementById(`btn-iniciar-${modulo.id}`);
        const btnDetener = document.getElementById(`btn-detener-${modulo.id}`);
        if (!estadoBadge || !btnIniciar || !btnDetener) {
            return;
        }

        if (modulo.estado === "running") {
            estadoBadge.className = "badge estado-badge bg-success";
            estadoBadge.innerHTML = '<i class="bi bi-circle-fill"></i> En ejecucion';
            btnIniciar.style.display = "none";
            btnDetener.style.display = "block";
        } else {
            estadoBadge.className = "badge estado-badge bg-secondary";
            estadoBadge.innerHTML = '<i class="bi bi-circle-fill"></i> Detenido';
            btnIniciar.style.display = "block";
            btnDetener.style.display = "none";
        }
    });
}

function actualizarInfoSistema(estado) {
    document.getElementById("procesos-activos").textContent = estado.total_procesos;
    const badge = document.getElementById("sistema-estado");
    if (estado.total_procesos > 0) {
        badge.className = "badge bg-success fs-6";
        badge.textContent = "OPERATIVO";
    } else {
        badge.className = "badge bg-secondary fs-6";
        badge.textContent = "EN ESPERA";
    }
    document.getElementById("directorio-base").textContent = estado.directorio;
}

function actualizarTablaProcesos(procesos) {
    const tbody = document.getElementById("tabla-procesos-body");
    if (!procesos || procesos.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No hay procesos activos</td></tr>';
        return;
    }

    tbody.innerHTML = procesos
        .map((p) => {
            const inicio = new Date(p.inicio).toLocaleString();
            const cpu = p.cpu !== null ? `${p.cpu.toFixed(1)}%` : "--";
            const mem = p.memoria !== null ? `${p.memoria.toFixed(1)} MB` : "--";
            const stateClass = p.estado === "running" ? "success" : "secondary";
            return `<tr>
                <td>${p.nombre}</td>
                <td><code>${p.pid}</code></td>
                <td><span class="badge bg-${stateClass}">${p.estado}</span></td>
                <td>${inicio}</td>
                <td>${cpu}</td>
                <td>${mem}</td>
            </tr>`;
        })
        .join("");
}

async function lanzarModulo(moduloId) {
    try {
        const response = await fetch(`/api/lanzar/${moduloId}`, { method: "POST" });
        const res = await response.json();
        if (!res.success) {
            mostrarNotificacion("Error", res.error || "No se pudo iniciar", "error");
        } else {
            mostrarNotificacion("Modulo iniciado", res.mensaje, "success");
        }
        await actualizarEstado();
    } catch (error) {
        mostrarNotificacion("Error", "No se pudo iniciar el modulo", "error");
    }
}

async function detenerModulo(moduloId) {
    if (!confirm("Deseas detener este modulo?")) return;
    try {
        const response = await fetch(`/api/detener/${moduloId}`, { method: "POST" });
        const res = await response.json();
        if (!res.success) {
            mostrarNotificacion("Error", res.error || "No se pudo detener", "error");
        } else {
            mostrarNotificacion("Modulo detenido", res.mensaje, "info");
        }
        await actualizarEstado();
    } catch (error) {
        mostrarNotificacion("Error", "No se pudo detener el modulo", "error");
    }
}

async function detenerTodos() {
    if (!confirm("Deseas detener todos los modulos?")) return;
    try {
        const response = await fetch("/api/detener_todos", { method: "POST" });
        const res = await response.json();
        if (!res.success) {
            mostrarNotificacion("Aviso", "Algunos procesos no se detuvieron correctamente", "warning");
        } else {
            mostrarNotificacion("Sistema", `Se detuvieron ${res.detenidos.length} modulo(s)`, "success");
        }
        await actualizarEstado();
    } catch (error) {
        mostrarNotificacion("Error", "No se pudo detener todo", "error");
    }
}

async function cargarDashboardVivo() {
    const linea = document.getElementById("vivo-linea").value;
    const maquina = document.getElementById("vivo-maquina")?.value || "ALL";
    const windowN = document.getElementById("vivo-window").value;
    const response = await fetch(`/api/dashboard/vivo?linea=${encodeURIComponent(linea)}&maquina=${encodeURIComponent(maquina)}&window=${encodeURIComponent(windowN)}`);
    const data = await response.json();

    const stats = data.stats || {};
    document.getElementById("vivo-stats").textContent = `L${stats.linea || "-"} | ${stats.maquina || "ALL"} | muestras ${stats.muestras || 0} | salud prom ${stats.salud_promedio || 0}% | tc prom ${stats.tc_promedio || 0}s`;

    const rendLinea = Number(stats.rendimiento_linea || 0);
    document.getElementById("vivo-rend-linea").textContent = `${rendLinea}%`;
    document.getElementById("vivo-linea-tc").textContent = `TC real ${stats.tc_linea_real || 0}s / obj ${stats.tc_linea_objetivo || 0}s`;

    upsertChart(
        "chart-vivo-trend",
        "line",
        {
            labels: data.labels || [],
            datasets: [
                { label: "Salud", data: data.salud || [], borderColor: "#2ecc71", backgroundColor: "rgba(46,204,113,0.25)", yAxisID: "y" },
                { label: "Tiempo Ciclo", data: data.tiempo_ciclo || [], borderColor: "#3498db", backgroundColor: "rgba(52,152,219,0.25)", yAxisID: "y1" },
            ],
        },
        {
            responsive: true,
            interaction: { mode: "index", intersect: false },
            scales: {
                y: { position: "left", title: { display: true, text: "Salud %" } },
                y1: { position: "right", grid: { drawOnChartArea: false }, title: { display: true, text: "TC (s)" } },
            },
        }
    );

    const eventos = data.eventos || {};
    upsertChart(
        "chart-vivo-eventos",
        "bar",
        {
            labels: Object.keys(eventos),
            datasets: [{ label: "Eventos", data: Object.values(eventos), backgroundColor: "#f39c12" }],
        },
        { responsive: true }
    );

    const rendMaq = data.rendimiento_por_maquina || {};
    const maqSel = maquina || "ALL";
    const maqSelValue = maqSel !== "ALL" && rendMaq[maqSel] !== undefined ? Number(rendMaq[maqSel]) : null;
    document.getElementById("vivo-rend-maquina").textContent = maqSelValue !== null ? `${maqSelValue}%` : (maqSel === "ALL" ? "Selecciona maquina" : "Sin datos");

    const labelsMaq = Object.keys(rendMaq);
    const valsMaq = labelsMaq.map((k) => Number(rendMaq[k] || 0));
    const colorsMaq = valsMaq.map((v) => (v >= 85 ? "#2ecc71" : v >= 65 ? "#f1c40f" : "#e74c3c"));
    upsertChart(
        "chart-vivo-rend-maquinas",
        "bar",
        {
            labels: labelsMaq,
            datasets: [{ label: "Rendimiento %", data: valsMaq, backgroundColor: colorsMaq }],
        },
        {
            responsive: true,
            scales: {
                y: { min: 0, max: 110, title: { display: true, text: "Rend %" } },
            },
        }
    );
}

async function cargarDashboardLogs() {
    const response = await fetch("/api/dashboard/logs");
    const data = await response.json();

    const k = data.kpis || {};
    document.getElementById("kpi-total").textContent = k.total_ciclos || 0;
    document.getElementById("kpi-ok").textContent = k.ok || 0;
    document.getElementById("kpi-scrap").textContent = k.scrap || 0;
    document.getElementById("kpi-rend").textContent = `${k.rendimiento || 0}%`;

    const pareto = data.pareto || {};
    upsertChart("chart-logs-pareto", "bar", {
        labels: Object.keys(pareto),
        datasets: [{ label: "Frecuencia", data: Object.values(pareto), backgroundColor: "#e74c3c" }],
    });

    const calidad = data.calidad || {};
    upsertChart("chart-logs-calidad", "doughnut", {
        labels: Object.keys(calidad),
        datasets: [{ data: Object.values(calidad), backgroundColor: ["#2ecc71", "#e74c3c", "#f1c40f"] }],
    });
}

async function cargarDashboardOee() {
    const response = await fetch("/api/dashboard/oee");
    const data = await response.json();

    document.getElementById("oee-global").textContent = `${data.global || 0}%`;
    document.getElementById("rend-global").textContent = `${data.rendimiento_general || 0}%`;

    const lineas = data.lineas || {};
    const labels = Object.keys(lineas).map((k) => `Linea ${k}`);
    const rendimientos = Object.values(lineas).map((v) => v.rendimiento || 0);

    upsertChart("chart-oee-lineas", "bar", {
        labels,
        datasets: [
            { label: "Rendimiento %", data: rendimientos, backgroundColor: ["#16a085", "#2980b9"] },
        ],
    });

    ["1", "2"].forEach((lid) => {
        const m = lineas[lid] || {};
        const el = document.getElementById(`oee-l${lid}`);
        if (!el) return;
        el.innerHTML = `Rendimiento <strong>${m.rendimiento || 0}%</strong><br>TC real ${m.tc_promedio || 0}s | TC objetivo ${m.tc_objetivo || 0}s<br>OEE ${m.oee || 0}%`;

        const maqEl = document.getElementById(`oee-maq-l${lid}`);
        if (!maqEl) return;
        const mqs = m.maquinas || {};
        const keys = Object.keys(mqs);
        if (!keys.length) {
            maqEl.innerHTML = '<span class="text-muted">Sin datos por maquina</span>';
            return;
        }
        maqEl.innerHTML = keys
            .map((mk) => {
                const mm = mqs[mk] || {};
                return `<div><strong>${mk}</strong>: Rend ${mm.rendimiento || 0}% | TC ${mm.tc_promedio || 0}s / Obj ${mm.tc_objetivo || 0}s</div>`;
            })
            .join("");
    });
}

async function registrarMantenimiento() {
    const linea = Number(document.getElementById("mto-linea").value);
    const maquina = document.getElementById("mto-maquina").value;
    const accionId = Number(document.getElementById("mto-accion").value);
    const response = await fetch("/api/mantenimiento", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ linea: linea, maquina: maquina, accion_id: accionId }),
    });
    const data = await response.json();
    if (data.success) {
        mostrarNotificacion("Mantenimiento", `Registro creado para ${maquina}`, "success");
        await cargarMantenimiento();
    } else {
        mostrarNotificacion("Error", data.error || "No se pudo registrar", "error");
    }
}

function actualizarMaquinasMto() {
    const linea = document.getElementById("mto-linea").value;
    const maquinaSelect = document.getElementById("mto-maquina");
    const maquinas = {
        "1": ["Toda la línea", "Top cover feeding", "Pre-weighing", "Tim dispensing", "Avl Tim", "Weighing", "Install PCB", "Fastening 1", "Fastening 2", "Avl screw", "Top unloader"],
        "2": ["Toda la línea", "Top cover feeding", "Pre-weighing", "Tim dispensing", "Avl Tim", "Weighing", "Install PCB", "Fastening 1", "Fastening 2", "Avl screw", "Top unloader"]
    };
    const listasMaquinas = maquinas[linea] || ["Toda la línea"];
    maquinaSelect.innerHTML = listasMaquinas.map(m => `<option>${m}</option>`).join("");
}

async function cargarMantenimiento() {
    const response = await fetch("/api/mantenimiento");
    const data = await response.json();
    const rows = data.rows || [];
    const tbody = document.getElementById("tabla-mto-body");

    if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Sin registros</td></tr>';
        return;
    }

    tbody.innerHTML = rows
        .map((r) => `<tr><td>${r.Timestamp || ""}</td><td>${r.Linea}</td><td>${r.Maquina || "Toda la línea"}</td><td>${r.Accion}</td><td>${r.Duracion}s</td><td>${r.Salud_Final}%</td></tr>`)
        .join("");
}

function actualizarMaquinasMto() {
    const linea = document.getElementById("mto-linea").value;
    const maquinaSelect = document.getElementById("mto-maquina");
    const maquinas = {
        "1": ["Toda la línea", "Top cover feeding", "Pre-weighing", "Tim dispensing", "Avl Tim", "Weighing", "Install PCB", "Fastening 1", "Fastening 2", "Avl screw", "Top unloader"],
        "2": ["Toda la línea", "Top cover feeding", "Pre-weighing", "Tim dispensing", "Avl Tim", "Weighing", "Install PCB", "Fastening 1", "Fastening 2", "Avl screw", "Top unloader"]
    };
    const listasMaquinas = maquinas[linea] || ["Toda la línea"];
    maquinaSelect.innerHTML = listasMaquinas.map(m => `<option>${m}</option>`).join("");
}

// ==================== PREDICTIVO ====================
let _predData = null; // cache global para filtro de tabla

function _riskColor(risk) {
    if (risk >= 70) return "#e74c3c";
    if (risk >= 40) return "#f39c12";
    return "#2ecc71";
}

function _alertBadge(alerta) {
    const map = { CRITICO: "danger", ATENCION: "warning", NORMAL: "success" };
    return `<span class="badge bg-${map[alerta] || "secondary"}">${alerta}</span>`;
}

async function cargarPredictivo() {
    const line = document.getElementById("pred-linea").value;
    const startRaw = document.getElementById("pred-start").value;
    const endRaw = document.getElementById("pred-end").value;
    const start = startRaw ? startRaw.replace("T", " ") : "";
    const end = endRaw ? endRaw.replace("T", " ") : "";

    const response = await fetch(`/api/predictivo?linea=${encodeURIComponent(line)}&start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
    const data = await response.json();
    _predData = data;

    // Timestamp
    const tsEl = document.getElementById("pred-timestamp");
    if (tsEl) tsEl.textContent = "Generado: " + (data.generated_at || "").substring(0, 19);

    // Riesgo sistema
    const rSys = Number(data.riesgo_sistema || 0);
    const rSysEl = document.getElementById("pred-riesgo-sistema");
    if (rSysEl) {
        rSysEl.textContent = rSys.toFixed(1) + "%";
        rSysEl.style.color = _riskColor(rSys);
    }

    // Dona de riesgo sistema
    upsertChart("chart-pred-riesgo", "doughnut", {
        labels: ["Riesgo", "Margen"],
        datasets: [{ data: [rSys, Math.max(0, 100 - rSys)], backgroundColor: [_riskColor(rSys), "#ecf0f1"] }],
    }, { plugins: { legend: { display: true }, title: { display: true, text: "Riesgo Global del Sistema" } } });

    // Datos por línea
    const lineas = data.lineas || {};
    const l1 = lineas["1"];
    const l2 = lineas["2"];

    // KPIs de salud por línea
    _fillLineKpis("l1", l1);
    _fillLineKpis("l2", l2);

    // Gráfica de riesgo por máquina (barras horizontales, ambas líneas juntas)
    _renderRiskByMachine(lineas);

    // Gráfica tendencia de salud
    _renderHealthTrend(lineas);

    // Tabla detalle
    renderPredTabla();

    // Downtime por turno
    _renderShifts("chart-pred-shifts-l1", "Línea 1 - Downtime por Turno", l1);
    _renderShifts("chart-pred-shifts-l2", "Línea 2 - Downtime por Turno", l2);
}

function _fillLineKpis(tag, lineData) {
    const saludEl = document.getElementById(`pred-salud-${tag}`);
    const riskEl = document.getElementById(`pred-risk-${tag}`);
    const mtbfEl = document.getElementById(`pred-mtbf-${tag}`);
    const mttrEl = document.getElementById(`pred-mttr-${tag}`);
    const lastEl = document.getElementById(`pred-lastmto-${tag}`);

    if (!lineData) {
        if (saludEl) saludEl.textContent = "Sin datos";
        if (riskEl) riskEl.textContent = "";
        if (mtbfEl) mtbfEl.textContent = "--";
        if (mttrEl) mttrEl.textContent = "--";
        if (lastEl) lastEl.textContent = "--";
        return;
    }

    if (saludEl) {
        saludEl.textContent = lineData.salud_promedio.toFixed(1) + "%";
        saludEl.style.color = lineData.salud_promedio >= 90 ? "#2ecc71" : lineData.salud_promedio >= 70 ? "#f39c12" : "#e74c3c";
    }
    if (riskEl) {
        const r = lineData.riesgo_global;
        riskEl.innerHTML = `Riesgo: <strong style="color:${_riskColor(r)}">${r.toFixed(1)}%</strong>`;
    }
    if (mtbfEl) mtbfEl.textContent = lineData.mtbf_hours != null ? lineData.mtbf_hours.toFixed(1) + "h" : "N/A";
    if (mttrEl) mttrEl.textContent = lineData.mttr_minutes != null ? lineData.mttr_minutes.toFixed(1) + "min" : "N/A";
    if (lastEl) lastEl.textContent = lineData.last_maintenance || "Sin registro";
}

function _renderRiskByMachine(lineas) {
    const labels = [];
    const valores = [];
    const colores = [];

    for (const [lid, ldata] of Object.entries(lineas)) {
        for (const m of (ldata.maquinas || [])) {
            labels.push(`L${lid} ${m.maquina}`);
            valores.push(m.riesgo);
            colores.push(_riskColor(m.riesgo));
        }
    }

    upsertChart("chart-pred-maquinas", "bar", {
        labels: labels,
        datasets: [{
            label: "Riesgo %",
            data: valores,
            backgroundColor: colores,
            borderWidth: 0,
        }],
    }, {
        indexAxis: "y",
        scales: { x: { min: 0, max: 100, title: { display: true, text: "Riesgo %" } } },
        plugins: { legend: { display: false }, title: { display: true, text: "Riesgo por Máquina (ambas líneas)" } },
    });
}

function _renderHealthTrend(lineas) {
    const datasets = [];
    const palette = { "1": "#3498db", "2": "#e67e22" };
    let maxLabels = [];

    for (const [lid, ldata] of Object.entries(lineas)) {
        // Pick the machine with the highest risk for trend display
        const mostRisky = (ldata.maquinas || []).slice(0, 3); // top 3 riskiest
        for (const m of mostRisky) {
            const trend = m.salud_trend || {};
            const lbls = trend.labels || [];
            const vals = trend.valores || [];
            if (lbls.length > maxLabels.length) maxLabels = lbls;
            datasets.push({
                label: `L${lid} ${m.maquina}`,
                data: vals,
                borderColor: palette[lid] || "#95a5a6",
                fill: false,
                tension: 0.3,
                pointRadius: 1,
                borderWidth: 2,
            });
        }
    }

    upsertChart("chart-pred-salud-trend", "line", {
        labels: maxLabels,
        datasets: datasets,
    }, {
        scales: { y: { min: 50, max: 105, title: { display: true, text: "Salud %" } } },
        plugins: { title: { display: true, text: "Tendencia Salud - Máquinas de Mayor Riesgo" }, legend: { position: "bottom" } },
    });
}

function renderPredTabla() {
    const data = _predData;
    if (!data) return;
    const filtro = (document.getElementById("pred-tabla-linea") || {}).value || "all";
    const tbody = document.getElementById("pred-tabla-body");
    if (!tbody) return;

    let rows = [];
    for (const [lid, ldata] of Object.entries(data.lineas || {})) {
        if (filtro !== "all" && filtro !== lid) continue;
        for (const m of (ldata.maquinas || [])) {
            rows.push({ lid, ...m });
        }
    }

    if (rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="11" class="text-center text-muted">Sin datos</td></tr>';
        return;
    }

    // Sort by risk descending
    rows.sort((a, b) => b.riesgo - a.riesgo);

    tbody.innerHTML = rows.map(r => {
        const tendIcon = r.tendencia_salud > 0 ? '<span class="text-success">▲</span>' :
                         r.tendencia_salud < 0 ? '<span class="text-danger">▼</span>' : '<span class="text-muted">━</span>';
        return `<tr>
            <td>${r.lid}</td>
            <td><strong>${r.maquina}</strong></td>
            <td style="color:${r.salud_actual >= 90 ? '#2ecc71' : r.salud_actual >= 70 ? '#f39c12' : '#e74c3c'}">${r.salud_actual.toFixed(1)}%</td>
            <td>${tendIcon} ${r.tendencia_salud > 0 ? '+' : ''}${r.tendencia_salud.toFixed(1)}</td>
            <td>${r.tc_promedio.toFixed(1)}s</td>
            <td>${r.tc_objetivo.toFixed(1)}s</td>
            <td style="color:${r.tc_desviacion_pct > 5 ? '#e74c3c' : r.tc_desviacion_pct > 2 ? '#f39c12' : '#2ecc71'}">${r.tc_desviacion_pct > 0 ? '+' : ''}${r.tc_desviacion_pct.toFixed(1)}%</td>
            <td>${r.errores}</td>
            <td>${r.scraps}</td>
            <td><strong style="color:${_riskColor(r.riesgo)}">${r.riesgo.toFixed(1)}%</strong></td>
            <td>${_alertBadge(r.alerta)}</td>
        </tr>`;
    }).join("");
}

function _renderShifts(canvasId, title, lineData) {
    if (!lineData) {
        upsertChart(canvasId, "bar", { labels: [], datasets: [] }, {});
        return;
    }
    const shifts = lineData.downtime_by_shift || {};
    upsertChart(canvasId, "bar", {
        labels: ["Mañana", "Tarde", "Noche"],
        datasets: [{
            label: "Downtime (min)",
            data: [
                Number(shifts.Morning || 0),
                Number(shifts.Afternoon || 0),
                Number(shifts.Night || 0),
            ],
            backgroundColor: ["#f1c40f", "#e67e22", "#2c3e50"],
        }],
    }, { plugins: { title: { display: true, text: title }, legend: { display: false } } });
}

function upsertChart(canvasId, type, data, options = {}) {
    if (charts[canvasId]) {
        charts[canvasId].data = data;
        charts[canvasId].options = options;
        charts[canvasId].update();
        return;
    }
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    charts[canvasId] = new Chart(canvas, { type, data, options });
}

function mostrarNotificacion(titulo, mensaje, tipo = "info") {
    const toast = document.getElementById("notification-toast");
    const toastTitle = document.getElementById("toast-title");
    const toastMessage = document.getElementById("toast-message");
    toastTitle.textContent = titulo;
    toastMessage.textContent = mensaje;

    toast.className = "toast";
    if (tipo === "success") toast.classList.add("toast-success");
    if (tipo === "error") toast.classList.add("toast-error");
    if (tipo === "info") toast.classList.add("toast-info");

    const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: 3500 });
    bsToast.show();
}

async function cargarDashboardLineas() {
    await cargarDetalleLinea();
}

async function cargarDetalleLinea() {
    const linea = document.getElementById("linea-select").value;
    const response = await fetch(`/api/linea/${linea}`);
    const data = await response.json();
    
    if (data.error) {
        document.getElementById("linea-rend").textContent = "--";
        return;
    }
    
    // KPI
    const kpi = data.kpi || {};
    document.getElementById("linea-rend").textContent = `${kpi.rendimiento || 0}%`;
    document.getElementById("linea-tc-real").textContent = `${kpi.tc_real || 0}s`;
    document.getElementById("linea-tc-obj").textContent = `${kpi.tc_objetivo || 0}s`;
    document.getElementById("linea-ciclos").textContent = `${kpi.total_ciclos || 0}`;
    
    // Actualizar dropdown de máquinas
    const rendMaq = data.rendimiento_por_maquina || {};
    const maquinas = ["Toda la línea", ...Object.keys(rendMaq)];
    const maqSelect = document.getElementById("linea-maquina-select");
    maqSelect.innerHTML = maquinas.map(m => `<option>${m}</option>`).join("");
    
    // Máquinas en mantenimiento
    const mtoList = data.maquinas_en_mantenimiento || [];
    const mtoDiv = document.getElementById("linea-mto-list");
    if (mtoList.length === 0) {
        mtoDiv.innerHTML = '<span class="text-success">✓ Todas disponibles</span>';
    } else {
        mtoDiv.innerHTML = mtoList.map(m => `<span class="badge bg-danger">${m}</span>`).join(' ');
    }
    
    // Rendimiento por máquina
    const maqDiv = document.getElementById("linea-maquinas-list");
    const maqBars = Object.entries(rendMaq).map(([maq, rend]) => {
        const color = rend >= 85 ? "bg-success" : rend >= 65 ? "bg-warning" : "bg-danger";
        return `<div class="d-flex justify-content-between align-items-center mb-2"><small>${maq}</small><div class="progress" style="width:60%; height:20px;"><div class="progress-bar ${color}" style="width:${rend}%">${rend.toFixed(0)}%</div></div></div>`;
    }).join('');
    maqDiv.innerHTML = maqBars || '<span class="text-muted">Sin datos</span>';
    
    // Últimos mantenimientos
    const mtoRecs = data.ultimos_mantenimientos || [];
    const mtoTable = document.getElementById("linea-mto-table");
    if (mtoRecs.length === 0) {
        mtoTable.innerHTML = '<tr><td colspan="5" class="text-center text-muted">Sin registros</td></tr>';
    } else {
        mtoTable.innerHTML = mtoRecs.map(r => 
            `<tr><td>${r.timestamp}</td><td>${r.maquina}</td><td>${r.accion}</td><td>${r.duracion}s</td><td>${r.salud_final}%</td></tr>`
        ).join('');
    }
}

async function registrarMtoLinea() {
    const linea = Number(document.getElementById("linea-select").value);
    const maquina = document.getElementById("linea-maquina-select").value;
    const accionId = Number(document.getElementById("linea-accion-select").value);
    
    const response = await fetch("/api/mantenimiento", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ linea: linea, maquina: maquina, accion_id: accionId }),
    });
    
    const result = await response.json();
    if (result.success) {
        mostrarNotificacion("Mantenimiento", `Registro creado para ${maquina} en Línea ${linea}`, "success");
        // Esperar un momento y recargar
        await new Promise(r => setTimeout(r, 500));
        await cargarDetalleLinea();
    } else {
        mostrarNotificacion("Error", result.error || "No se pudo registrar", "error");
    }
}

window.addEventListener("beforeunload", () => {
    if (intervaloActualizacion) {
        clearInterval(intervaloActualizacion);
    }
});
