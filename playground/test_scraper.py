from bs4 import BeautifulSoup
from curl_cffi import requests


def test_kleinanzeigen_scraper():
    url = "https://www.kleinanzeigen.de/s-macbook/k0"

    print(f"🚀 Starte Schnappster-Test für: {url}")
    print("Sende Request mit Chrome-Impersonation...")

    try:
        response = requests.get(
            url,
            impersonate="chrome120",
            headers={
                "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            },
            timeout=10,
        )

        print(f"\n📡 Status Code: {response.status_code}")

        if response.status_code == 200:
            # HIER IST DIE ÄNDERUNG: Wir nutzen 'lxml' statt 'html.parser'
            soup = BeautifulSoup(response.text, "lxml")
            page_title = soup.title.text if soup.title else "Kein Titel gefunden"
            print(f"📄 Seiten-Titel: {page_title}")

            html_content = response.text.lower()
            if (
                "datadome" in html_content
                or "captcha" in html_content
                or "überprüfung" in html_content
            ):
                print("\n⚠️ WARNUNG: Bot-Sperre (Captcha) erkannt!")
            else:
                print("\n✅ ERFOLG: Keine offensichtliche Bot-Sperre erkannt!")

                listings = soup.find_all("article", class_="aditem")
                print(f"📦 Gefundene Inserate auf der Seite: {len(listings)}")

                if len(listings) > 0:
                    first_title_elem = listings[0].find("a", class_="ellipsis")
                    if first_title_elem:
                        print(f"Beispiel-Fund: {first_title_elem.text.strip()}")

        elif response.status_code in [403, 429]:
            print("\n❌ BLOCKIERT: Kleinanzeigen hat uns direkt abgewiesen.")
        else:
            print(f"\n❓ Unerwarteter Status: {response.status_code}")

    except Exception as e:
        print(f"\n💥 Fehler beim Ausführen des Requests: {e}")


if __name__ == "__main__":
    test_kleinanzeigen_scraper()
