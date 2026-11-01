import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import rankings
import reporte


def cambio(nombre, desde, hasta, cargo, variacion):
    return {
        "nombre": nombre,
        "periodo_desde": "2025-01",
        "grado_desde": desde,
        "periodo_hasta": "2025-02",
        "grado_hasta": hasta,
        "meses_entre": 1,
        "cargo_desde": cargo,
        "cargo_hasta": cargo,
        "variacion": variacion,
    }


class RankingsTest(unittest.TestCase):
    def setUp(self):
        self.filas = [
            cambio("Ana Perez", "15", "14", "Fiscalizador", "15 -> 14"),
            cambio("Beto Soto", "15", "14", "Fiscalizador", "15 -> 14"),
            cambio("Carla Rojas", "16", "15", "Administrativo", "16 -> 15"),
        ]

    def test_ranking_cargos(self):
        ranking = rankings.cargos(self.filas)
        self.assertEqual(ranking[0]["cargo"], "Fiscalizador")
        self.assertEqual(ranking[0]["cambios"], 2)
        self.assertEqual(ranking[0]["personas"], 2)
        self.assertEqual(ranking[1]["cargo"], "Administrativo")

    def test_ranking_personas(self):
        filas = self.filas + [
            cambio("Ana Perez", "14", "13", "Fiscalizador", "14 -> 13"),
        ]
        ranking = rankings.personas(filas)
        self.assertEqual(ranking[0]["nombre"], "Ana Perez")
        self.assertEqual(ranking[0]["cambios"], 2)
        self.assertEqual(ranking[0]["grados"], "15 -> 14 -> 13")

    def test_markdown_escapa_pipes(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "ranking.md"
            reporte.escribir_md(path, "T", "R", ["Cargo"], [["a|b"]])
            self.assertIn("a\\|b", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
