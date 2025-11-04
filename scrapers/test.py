import requests
from bs4 import BeautifulSoup

def test():
    # Starting page
    start_url = "http://reader.dia.hu/online-reader/open?epubId=7871&component=Zavada_Pal-A_fenykepesz_utokora-00010&locale=hu"

    # Fetch the page
    resp = requests.get(start_url)
    soup = BeautifulSoup(resp.text, "html.parser")

    urls = []

    # Example extraction from <option> tags (dropdown navigation)
    for option in soup.select("option"):
        component_id = option.get("value")
        if component_id:
            # Build the URL for each chapter/section
            url = f"http://reader.dia.hu/online-reader/open?epubId=7871&component={component_id}&locale=hu"
            urls.append(url)

    # Example: extraction from <li> tags (table of contents)
    for li in soup.select("ul > li"):
        # Assuming data-component or similar attribute; adjust as needed
        component_id = li.get("data-component")
        print(component_id)
        if component_id:
            url = f"http://reader.dia.hu/online-reader/open?epubId=7871&component={component_id}&locale=hu"
            urls.append(url)
        else:
            print("No component ID found")

    # Print all discovered URLs
    for u in urls:
        print(u)



if __name__ == "__main__":
    test()


