import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import fuente as f
import grados

BOTON = ["Año", "Mes", "Estamento", "Nombre completo",
         "Cargo o función", "Grado EUS o jornada"]


def escribir(path: Path, filas: list[list[str]]) -> None:
    f.escribir_csv(path, BOTON, filas)


class GradosTest(unittest.TestCase):
    def test_cambio_y_deduplicacion(self):
        with TemporaryDirectory() as tmp:
            d = Path(tmp)
            escribir(d / "2025-01.csv", [
                ["2025", "Enero", "Contrata", "Ana Perez", "Fiscalizador", "15"],
                ["2025", "Enero", "Contrata", "Beto Soto", "Administrativo", "12"],
            ])
            escribir(d / "2025-02.csv", [
                ["2025", "Febrero", "Contrata", "Ana Perez", "Fiscalizador", "14"],
                ["2025", "Febrero", "Contrata", "Beto Soto", "Administrativo", "12"],
            ])
            escribir(d / "2025.csv", [
                ["2025", "Enero", "Contrata", "Ana Perez", "Fiscalizador", "15"],
                ["2025", "Enero", "Contrata", "Beto Soto", "Administrativo", "12"],
                ["2025", "Febrero", "Contrata", "Ana Perez", "Fiscalizador", "14"],
                ["2025", "Febrero", "Contrata", "Beto Soto", "Administrativo", "12"],
            ])

            cambios, total, unicos, personas, ambiguos = grados.analizar(
                sorted(d.glob("*.csv")))

            self.assertEqual(total, 8)
            self.assertEqual(unicos, 4)
            self.assertEqual(personas, 2)
            self.assertEqual(ambiguos, 0)
            self.assertEqual(len(cambios), 1)
            self.assertEqual(cambios[0]["nombre"], "Ana Perez")
            self.assertEqual(cambios[0]["variacion"], "15 -> 14")
            self.assertEqual(cambios[0]["meses_entre"], 1)

    def test_formato_nacional(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "nacional.csv"
            f.escribir_csv(path, [
                "anyo", "Mes", "Nombres", "Paterno", "Materno",
                "grado_eus", "Tipo cargo",
            ], [
                ["2025", "Enero", "Ana", "Perez", "Diaz", "12", "Fiscalizador"],
                ["2025", "Febrero", "Ana", "Perez", "Diaz", "11", "Fiscalizador"],
            ])

            cambios, *_ = grados.analizar([path])

            self.assertEqual(len(cambios), 1)
            self.assertEqual(cambios[0]["nombre"], "Ana Perez Diaz")
            self.assertEqual(cambios[0]["variacion"], "12 -> 11")


if __name__ == "__main__":
    unittest.main()
