"""Gera uma entrega Windows validada. Nunca inclui os dados da academia."""

import argparse
import ast
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from studio_fd.utils.versioning import version_tuple


def read_version(project: Path) -> str:
    tree = ast.parse((project / "studio_fd/__init__.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets):
            version = ast.literal_eval(node.value)
            version_tuple(version)
            return version
    raise ValueError("Não foi encontrada a versão em studio_fd/__init__.py.")


def validate_release(project: Path, version: str) -> Path:
    if version_tuple(version) <= version_tuple(read_version(project)):
        raise ValueError("A nova versão precisa ser maior que a versão atual do projeto.")
    installer = project / "release" / f"StudioFDPerformance-Setup-{version}.exe"
    if any(installer.parent.glob(installer.name + "*")):
        raise ValueError("Essa entrega já existe. Escolha outro número; entregas antigas não são sobrescritas.")
    return installer


def write_metadata(project: Path, version: str) -> None:
    major, minor, patch = version_tuple(version)
    build = project / "build"
    build.mkdir(exist_ok=True)
    (build / "release_version.iss").write_text(
        f'#define AppVersion "{version}"\n#define VersionMS {major * 65536 + minor}\n#define VersionLS {patch * 65536}\n', encoding="utf-8")
    (build / "windows_version_info.txt").write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({major}, {minor}, {patch}, 0), prodvers=({major}, {minor}, {patch}, 0),
                   mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('041604B0', [
    StringStruct('CompanyName', 'Studio FD Performance'),
    StringStruct('FileDescription', 'Studio FD Performance'),
    StringStruct('FileVersion', '{version}.0'),
    StringStruct('InternalName', 'Studio FD Performance'),
    StringStruct('OriginalFilename', 'Studio FD Performance.exe'),
    StringStruct('ProductName', 'Studio FD Performance'),
    StringStruct('ProductVersion', '{version}'),
  ])]), VarFileInfo([VarStruct('Translation', [1046, 1200])])]
)
""", encoding="utf-8")


@contextmanager
def release_lock(project: Path):
    import msvcrt

    (project / "build").mkdir(exist_ok=True)
    with (project / "build/release.lock").open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise ValueError("Já existe uma geração de atualização em andamento.") from error
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def generate(project: Path, version: str, notes: str, compiler: Path) -> Path:
    with release_lock(project):
        installer = validate_release(project, version)
        if not compiler.is_file():
            raise ValueError(f"Compilador não encontrado: {compiler}. Informe --inno-compiler com o caminho do ISCC.exe.")
        source = project / "studio_fd/__init__.py"
        original = source.read_bytes()
        updated, count = re.subn(rb'(?m)^__version__ = "[^"]+"', f'__version__ = "{version}"'.encode(), original)
        if count != 1:
            raise ValueError("A declaração __version__ precisa aparecer uma única vez.")
        stage = project / "build" / f"release-stage-{version}-{uuid4().hex[:8]}"
        stage.mkdir()
        env = os.environ.copy()
        env["PYINSTALLER_CONFIG_DIR"] = str(project / "build/pyinstaller-cache")
        env["PYTHONUTF8"] = "1"
        env["QT_QPA_PLATFORM"] = "offscreen"
        env.pop("STUDIO_FD_DATA_DIR", None)

        def run(label, args):
            print(f"\n{label}", flush=True)
            subprocess.run([str(arg) for arg in args], cwd=project, env=env, check=True)

        published = False
        companions = []
        try:
            source.write_bytes(updated)
            for cached in (project / "studio_fd/__pycache__").glob("__init__.*.pyc"):
                cached.unlink()
            write_metadata(project, version)
            run("1/5 Conferindo dependências e testes...", [sys.executable, "-m", "pip", "check"])
            run("Testando o sistema...", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
            run("2/5 Preparando o ícone...", [sys.executable, "tools/create_icon.py"])
            run("3/5 Montando o aplicativo...", [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "packaging/studio_fd.spec"])
            run("4/5 Testando abertura e persistência do executável...", [sys.executable, "tools/test_frozen.py", project / "dist/Studio FD Performance/Studio FD Performance.exe"])
            run("5/5 Criando o instalador...", [compiler, f"/O{stage}", project / "packaging/studio_fd.iss"])
            built = stage / installer.name
            with built.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest().upper()
            (stage / (installer.name + ".sha256")).write_text(f"{digest}  {installer.name}\n", encoding="ascii")
            instructions = f"""STUDIO FD PERFORMANCE — ATUALIZAÇÃO {version}

O que mudou: {notes.strip() or 'Melhorias e correções do sistema.'}

1. Feche o Studio no computador da academia.
2. Copie {installer.name} para esse computador (presencialmente ou pelo AnyDesk).
3. Na mesma conta Windows usada pela academia, execute o instalador e mantenha a pasta sugerida.
4. Abra o Studio, confira a versão no menu lateral e confira os alunos cadastrados.

Não é necessário desinstalar a versão anterior nem instalar Python.
Os dados ficam em %LOCALAPPDATA%\\StudioFDPerformance\\data.
Na primeira abertura com dados existentes, a nova versão cria uma cópia em data\\backups
antes das migrações. Se a cópia falhar, a abertura é interrompida.
Essa cópia local não substitui backup externo periódico. Não instale versões antigas.
O instalador não contém cadastros. Atualização manual, sem envio automático para a academia.
"""
            (stage / (installer.name + ".LEIA-ME.txt")).write_text(instructions, encoding="utf-8-sig")
            (stage / (installer.name + ".json")).write_text(json.dumps({
                "product": "studio-fd-performance", "version": version,
                "created_at": datetime.now(timezone.utc).isoformat(), "notes": notes,
                "file": installer.name, "sha256": digest, "bytes": built.stat().st_size,
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            installer.parent.mkdir(exist_ok=True)
            # Windows Path.rename recusa destino existente. Publica o .exe por último.
            for suffix in (".sha256", ".LEIA-ME.txt", ".json"):
                destination = installer.parent / (installer.name + suffix)
                (stage / (installer.name + suffix)).rename(destination)
                companions.append(destination)
            built.rename(installer)
            published = True
            print(f"\nPRONTO! Atualização {version}:\n{installer}\nInstruções: {installer.name}.LEIA-ME.txt", flush=True)
            return installer
        finally:
            if not published:
                for companion in companions:
                    companion.rename(stage / companion.name)
                if source.read_bytes() == updated:
                    source.write_bytes(original)
                    for cached in (project / "studio_fd/__pycache__").glob("__init__.*.pyc"):
                        cached.unlink()
                print(f"\nA entrega não foi concluída. Confira o erro acima. Arquivos de diagnóstico: {stage}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera uma nova versão instalável do Studio FD Performance.")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--version")
    parser.add_argument("--notes", default="")
    parser.add_argument("--inno-compiler", type=Path, default=PROJECT / "build/toolchain/inno/ISCC.exe")
    args = parser.parse_args()
    try:
        version, notes = args.version, args.notes
        if args.interactive:
            current = read_version(PROJECT)
            major, minor, patch = version_tuple(current)
            suggestion = f"{major}.{minor}.{patch + 1}"
            print(f"STUDIO FD — GERAR ATUALIZAÇÃO\nVersão atual: {current}\nSalve seus arquivos no VS Code antes de continuar.\n")
            version = version or input(f"Nova versão [Enter para {suggestion}]: ").strip() or suggestion
            notes = notes or input("O que mudou nesta versão? ").strip()
        if not version:
            parser.error("informe --version ou use --interactive")
        generate(PROJECT, version, notes, args.inno_compiler.resolve())
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"\nNão foi possível gerar a atualização: {error}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nGeração cancelada.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
