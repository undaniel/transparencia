import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import fuente as f


class FuenteTest(unittest.TestCase):
    def test_mes_numero(self):
        self.assertEqual(f.mes_numero("Septiembre"), 9)
        self.assertEqual(f.mes_numero("setiembre"), 9)
        self.assertEqual(f.mes_numero("09"), 9)
        self.assertEqual(f.mes_numero(12), 12)
        self.assertIsNone(f.mes_numero("13"))
        self.assertIsNone(f.mes_numero(""))

    def test_norm(self):
        self.assertEqual(f.norm("  José   Ángel "), "jose angel")

    def test_columnas_boton(self):
        idx = f.detectar_columnas([
            "Año", "Mes", "Estamento", "Nombre completo",
            "Cargo o función", "Grado EUS o jornada",
        ])
        self.assertEqual(idx["anio"], 0)
        self.assertEqual(idx["mes"], 1)
        self.assertEqual(idx["nombre"], 3)
        self.assertEqual(idx["cargo"], 4)
        self.assertEqual(idx["grado"], 5)

    def test_columnas_nacional(self):
        idx = f.detectar_columnas([
            "anyo", "Mes", "Nombres", "Paterno", "Materno",
            "grado_eus", "Tipo cargo",
        ])
        self.assertEqual(idx["anio"], 0)
        self.assertEqual(idx["nombres"], 2)
        self.assertEqual(idx["grado"], 5)
        self.assertEqual(idx["cargo"], 6)

    def test_ida_y_vuelta_csv(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "prueba.csv"
            f.escribir_csv(path, ["Año", "Mes"], [["2026", "Enero"]])
            self.assertEqual(f.leer_csv(path),
                             [["Año", "Mes"], ["2026", "Enero"]])


if __name__ == "__main__":
    unittest.main()
