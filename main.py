"""CLI para download de arquivos DOU via portal INLABS."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from inlabs_client import InlabsClient, InlabsError
from xml_processor import XMLProcessor


def cmd_dates(client: InlabsClient, args: argparse.Namespace) -> None:
    """Lista datas disponíveis."""
    dates = client.list_available_dates()
    limit = args.limit or len(dates)
    print(f"Datas disponíveis ({min(limit, len(dates))} de {len(dates)}):")
    for d in dates[:limit]:
        print(f"  {d}")


def cmd_files(client: InlabsClient, args: argparse.Namespace) -> None:
    """Lista arquivos de uma data."""
    files = client.list_files(args.date)
    print(f"Arquivos de {args.date}: {len(files)}")
    for f in files:
        print(f"  {f['name']:50s} {f['size']:>12s}  {f['modified']}")


def cmd_pdf(client: InlabsClient, args: argparse.Namespace) -> None:
    """Download de PDFs."""
    sections = args.sections.split(",") if args.sections else None
    print(f"Baixando PDFs de {args.date}...")
    downloaded = client.download_pdf(
        args.date,
        sections=sections,  # type: ignore[arg-type]
        output_dir=args.output,
        include_extras=not args.no_extras,
    )
    if downloaded:
        print(f"\n{len(downloaded)} arquivo(s) baixado(s).")
    else:
        print("\nNenhum arquivo encontrado para essa data.")


def cmd_zip(client: InlabsClient, args: argparse.Namespace) -> None:
    """Download de ZIPs (XML)."""
    sections = args.sections.split(",") if args.sections else None
    print(f"Baixando ZIPs de {args.date}...")
    downloaded = client.download_zip(
        args.date,
        sections=sections,  # type: ignore[arg-type]
        output_dir=args.output,
    )
    if downloaded:
        print(f"\n{len(downloaded)} arquivo(s) baixado(s).")
    else:
        print("\nNenhum arquivo encontrado para essa data.")


def cmd_mre(client: InlabsClient, args: argparse.Namespace) -> None:
    """Busca publicações do Ministério das Relações Exteriores em uma data específica."""
    output_dir = Path(args.output)
    zip_files = list(output_dir.glob(f"{args.date}-*.zip"))

    if not zip_files and args.download:
        print(f"ZIPs não encontrados para {args.date} no diretório {output_dir}. Baixando...")
        zip_files = client.download_zip(args.date, output_dir=output_dir)

    if not zip_files:
        print(f"Nenhum arquivo ZIP encontrado para {args.date}. Use --download para baixar.")
        return

    processor = XMLProcessor()
    found_count = 0
    print(f"Buscando publicações do MRE em {len(zip_files)} arquivo(s) ZIP...\n")

    for zip_path in zip_files:
        print(f"  Processando {zip_path.name}...")
        for article in processor.filter_by_org(zip_path, "Ministério das Relações Exteriores"):
            found_count += 1
            print("\n" + "=" * 80)
            print(f"ID:        {article['id']}")
            print(f"TIPO:      {article['type']}")
            print(f"CATEGORIA: {article['category']}")
            print(f"TÍTULO:    {article['title']}")
            print(f"EMENTA:    {article['ementa']}")
            print(f"ARQUIVO:   {zip_path.name}/{article['xml_name']}")

    if found_count == 0:
        print("\nNenhuma publicação do MRE encontrada nesta data.")
    else:
        print("\n" + "=" * 80)
        print(f"Total de publicações encontradas: {found_count}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download de arquivos DOU via portal INLABS"
    )
    parser.add_argument(
        "-o", "--output", default="downloads", help="Diretório de saída (padrão: downloads)"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # dates
    subparsers.add_parser("dates", help="Lista datas disponíveis").add_argument(
        "-n", "--limit", type=int, default=10, help="Número de datas (padrão: 10)"
    )

    # files
    sub_files = subparsers.add_parser("files", help="Lista arquivos de uma data")
    sub_files.add_argument("date", help="Data no formato YYYY-MM-DD")

    # pdf
    sub_pdf = subparsers.add_parser("pdf", help="Download de PDFs assinados")
    sub_pdf.add_argument("date", help="Data no formato YYYY-MM-DD")
    sub_pdf.add_argument(
        "-s", "--sections", help="Seções separadas por vírgula (do1,do2,do3)"
    )
    sub_pdf.add_argument("--no-extras", action="store_true", help="Não baixar edições extras")

    # zip
    sub_zip = subparsers.add_parser("zip", help="Download de ZIPs (XML)")
    sub_zip.add_argument("date", help="Data no formato YYYY-MM-DD")
    sub_zip.add_argument(
        "-s", "--sections", help="Seções separadas por vírgula (DO1,DO2,DO3,DO1E,DO2E,DO3E)"
    )

    # mre
    sub_mre = subparsers.add_parser("mre", help="Busca publicações do MRE")
    sub_mre.add_argument("date", help="Data no formato YYYY-MM-DD")
    sub_mre.add_argument(
        "--download", action="store_true", help="Baixar ZIPs se não existirem localmente"
    )

    args = parser.parse_args()

    try:
        client = InlabsClient.from_env()
        client.login()
        print(f"Autenticado como {client.session_cookie[:20]}...\n")

        if args.command == "dates":
            cmd_dates(client, args)
        elif args.command == "files":
            cmd_files(client, args)
        elif args.command == "pdf":
            cmd_pdf(client, args)
        elif args.command == "zip":
            cmd_zip(client, args)
        elif args.command == "mre":
            cmd_mre(client, args)

    except InlabsError as e:
        print(f"Erro: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
