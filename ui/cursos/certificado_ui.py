"""
Interfaz para descargar el certificado de un curso aprobado.

Lo usan la pantalla de resultados del examen y el panel del curso: ambos
llaman a `descargar_certificado`, que se ocupa de todo el flujo:

    emitir (si hace falta) -> «Guardar como» -> generar el PDF -> ofrecer abrirlo

El generador (reportlab) se importa recién al usarlo, así que si la librería
no está instalada la aplicación sigue arrancando y solo falla esta acción,
con un mensaje claro.
"""

from pathlib import Path

from PyQt6.QtCore import QStandardPaths, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidget


def _carpeta_inicial() -> Path:
    documentos = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
    return Path(documentos) if documentos else Path.home()


def descargar_certificado(parent: QWidget | None, db, curso_id: int | None) -> bool:
    """
    Guarda el certificado del curso como PDF. Devuelve True si se guardó.

    Si el curso aún no está aprobado no hay certificado y solo se avisa.
    """
    if db is None or curso_id is None:
        return False

    certificado = db.obtener_o_emitir_certificado(curso_id)
    if certificado is None:
        QMessageBox.information(
            parent,
            "Certificado no disponible",
            "El certificado se obtiene al aprobar la evaluación final del curso.",
        )
        return False

    try:
        from services.certificado_service import generar_certificado_pdf, nombre_archivo_sugerido
    except ImportError:
        QMessageBox.critical(
            parent,
            "Falta una dependencia",
            "Para generar certificados hace falta la librería reportlab.\n\n"
            "Instálala con:\n    pip install reportlab",
        )
        return False

    sugerido = _carpeta_inicial() / nombre_archivo_sugerido(certificado)
    ruta, _filtro = QFileDialog.getSaveFileName(
        parent, "Guardar certificado", str(sugerido), "Documento PDF (*.pdf)"
    )
    if not ruta:
        return False   # el usuario canceló

    try:
        destino = generar_certificado_pdf(certificado, ruta)
    except Exception as error:   # carpeta sin permisos, archivo abierto en otro programa, etc.
        QMessageBox.critical(
            parent, "No se pudo guardar el certificado", f"{type(error).__name__}: {error}"
        )
        return False

    caja = QMessageBox(
        QMessageBox.Icon.Information,
        "Certificado guardado",
        f"Tu certificado se guardó en:\n{destino}",
        parent=parent,
    )
    boton_abrir = caja.addButton("Abrir", QMessageBox.ButtonRole.AcceptRole)
    caja.addButton("Cerrar", QMessageBox.ButtonRole.RejectRole)
    caja.exec()
    if caja.clickedButton() == boton_abrir:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(destino)))
    return True
