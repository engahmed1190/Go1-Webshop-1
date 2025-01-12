import frappe
import json
import os
import time
from frappe.utils import encode, get_files_path
import requests
from frappe import _
from frappe.utils.background_jobs import enqueue
# from go1_webshop.go1_webshop.doctype.override_doctype.builder_page import log_css_template

MAX_LOG_LENGTH = 140
MAX_METHOD_LENGTH = 255


def make_error_log(message=""):
    frappe.log_error(message, frappe.get_traceback())


# Don't Remove this API
# @frappe.whitelist(allow_guest=True)
# def fetch_themes_from_external_url():
#     external_url = "http://192.168.0.157:8225/api/method/go1_webshop_theme.go1_webshop_theme.utils.get_theme_list"
#     api_key = "4d689e50dcec946"
#     api_secret = "aaf1bc1c3c7e24a"

#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"token {api_key}:{api_secret}"
#     }
#     try:
#         response = requests.post(external_url,headers=headers)
#         response.raise_for_status()
#         themes = response.json()
#         for theme in themes.get('message'):
#             theme['theme_image'] = domain_name + theme['theme_image']
#         return themes.get('message', [])
#     except requests.exceptions.RequestException as e:
#         frappe.throw(_('Error fetching themes from external URL: {0}').format(str(e)))


@frappe.whitelist(allow_guest=True)
def fetch_erp_ecommerce_themes_from_external_url():
    webshop_theme_settings = frappe.get_single("Go1 Webshop Theme Settings")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"token {webshop_theme_settings.api_key}:{webshop_theme_settings.api_secret}"
    }
    external_url = f"{webshop_theme_settings.url}/api/method/go1_webshop_theme.go1_webshop_theme.utils.fetch_erp_ecommerce_themes"

    try:
        response = requests.post(external_url, headers=headers)
        response.raise_for_status()
        themes = response.json()
        for theme in themes.get('message'):
            theme['theme_image'] = webshop_theme_settings.url + \
                theme['theme_image']
        return themes.get('message', [])
    except requests.exceptions.RequestException as e:
        frappe.throw(
            _('Error fetching themes from external URL: {0}').format(str(e)))


@frappe.whitelist(allow_guest=True)
def handle_specific_endpoint(values):
    frappe.msgprint(f"Received data: {values}")
    return values


@frappe.whitelist(allow_guest=True)
def after_install():
    insert_custom_fields()
    # insert_component()
    get_theme()


@frappe.whitelist(allow_guest=True)
def insert_custom_block():
    source_path = frappe.get_app_path("go1_webshop")
    file_path = os.path.join(
        source_path, "templates/js", "custom_html_block.json")
    data = json.load(open(file_path, "r"))
    if not frappe.db.exists(data[0].get("doctype"), data[0].get("name")):
        doc = frappe.new_doc(data[0].get("doctype"))
        doc.update(data[0])
        doc.insert(ignore_permissions=True, ignore_mandatory=True)
        frappe.db.commit()


@frappe.whitelist(allow_guest=True)
def insert_theme_selection_details():
    """ After migrate functionalities """

    update_webshop_dettings()
    insert_default_pages()
    clear_cache_for_current_site()


def update_webshop_dettings():
    """ Set the default values for Webshop Settings """

    try:
        company = frappe.db.get_all("Company")
        webshop_settings = frappe.get_single("Webshop Settings")
        webshop_settings.products_per_page = 20
        webshop_settings.enable_variants = 1
        webshop_settings.show_stock_availability = 1
        webshop_settings.show_price = 1
        webshop_settings.show_quantity_in_website = 1
        webshop_settings.enable_recommendations = 1
        webshop_settings.enable_wishlist = 1
        if company:
            webshop_settings.enabled = 1
            webshop_settings.company = company[0].name
            webshop_settings.price_list = "Standard Selling"
            webshop_settings.quotation_series = "SAL-QTN-.YYYY.-"
            webshop_settings.default_customer_group = "All Customer Groups"
        webshop_settings.save(ignore_permissions=True)
    except:
        make_error_log(
            message="Error in after_install.update_webshop_dettings")
        pass


def insert_default_pages():
    """ To insert the Default Builder Pages for browse themes """
    try:
        module_path = frappe.get_module_path("go1_webshop")
        folder_path = os.path.join(module_path, "default_pages")
        if os.path.exists(folder_path):
            read_file_path(folder_path, "builder_client_scripts.json")
            read_file_path(folder_path, "builder_components.json")
            insert_builder_pages(folder_path, "builder_pages.json")
    except:
        make_error_log(message="Error in after_install.insert_default_pages")
        pass


def insert_builder_pages(folder_path, file_name):
    """ To insert the Default Builder Pages """

    file_path = os.path.join(folder_path, file_name)
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
            if data:
                read_page_module_path(data)


def read_file_path(folder_path, file_name):
    """ To insert the Builder Client Scripts and Builder Components for Default Builder Pages """

    file_path = os.path.join(folder_path, file_name)
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
            if data:
                for k in data:
                    if k['doctype'] == "Builder Client Script":
                        if not frappe.db.exists({"doctype": k.get('doctype'), "name": k.get('name')}):
                            script_doc = frappe.get_doc(k).insert(
                                ignore_permissions=True, ignore_mandatory=True)
                            frappe.db.sql("""UPDATE `tabBuilder Client Script` SET name=%(c_name)s WHERE name=%(s_name)s""", {
                                          "c_name": k.get('name'), "s_name": script_doc.name})
                            frappe.db.commit()
                        else:
                            script_doc = frappe.get_doc(
                                "Builder Client Script", k.get('name'))
                            script_doc.update(k)
                            script_doc.save(ignore_permissions=True)
                    elif k['doctype'] == "Builder Component":
                        create_builder_component(k)


@frappe.whitelist(allow_guest=True)
def get_theme():
    themes = [
        {"theme_name": "Go1 Furniture Theme", "doctype": "Go1 Webshop Theme",
            "theme_image": "https://go1themes.tridotstech.com/files/Go1%20Furniture%20theme.png", "theme_route": "furniture_theme"},
        {"theme_name": "Go1 Cosmetics Theme", "doctype": "Go1 Webshop Theme",
         "theme_image": "https://go1themes.tridotstech.com/files/Cosmetics%20theme.png", "theme_route": "fashion_theme"}
    ]
    for theme in themes:
        exists = frappe.db.exists("Go1 Webshop Theme", {
                                  "theme_name": theme["theme_name"]})
        if not exists:
            doc = frappe.new_doc("Go1 Webshop Theme")
            doc.theme_name = theme["theme_name"]
            doc.theme_image = theme["theme_image"]
            doc.theme_route = theme["theme_route"]
            doc.insert(ignore_permissions=True, ignore_mandatory=True)
            frappe.db.commit()


@frappe.whitelist(allow_guest=True)
def insert_pages(theme, nodata=None):
    """ Deleting Old Theme Data """
    frappe.db.sql('''DELETE I
                    FROM `tabWishlist Item` I
                    INNER JOIN `tabWebsite Item` P ON P.name = I.website_item
                    WHERE P.is_go1_webshop_item = 1
                    ''')
    frappe.db.sql('''DELETE Q
                    FROM `tabQuotation` Q
                    INNER JOIN `tabQuotation Item` QI ON QI.parent = Q.name
                    INNER JOIN `tabItem` I ON QI.item_code = I.name
                    WHERE I.is_go1_webshop_item = 1
                ''')
    frappe.db.sql('DELETE FROM `tabItem` WHERE is_go1_webshop_item = 1')
    frappe.db.sql(
        'DELETE FROM `tabWebsite Item` WHERE is_go1_webshop_item = 1')
    frappe.db.sql('DELETE FROM `tabItem Group` WHERE is_go1_webshop_item = 1')
    frappe.db.sql('DELETE FROM `tabMobile Menu`')
    frappe.db.sql('DELETE FROM `tabItem Price` WHERE is_go1_webshop_item = 1')
    frappe.db.sql(
        'DELETE FROM `tabWebsite Slideshow Item` WHERE is_go1_webshop_item = 1')
    frappe.db.sql(
        'DELETE FROM `tabWebsite Slideshow` WHERE is_go1_webshop_item = 1')
    frappe.db.sql(
        'DELETE FROM `tabBuilder Page` WHERE is_go1_webshop_item = 1')
    frappe.db.sql(
        'DELETE FROM `tabBuilder Component` WHERE is_go1_webshop_item = 1')
    frappe.db.sql(
        'DELETE FROM `tabBuilder Client Script` WHERE is_go1_webshop_item = 1')

    def update_home_page(new_home_route):
        current_home_page = frappe.db.get_value(
            'Website Settings', 'Website Settings', 'home_page')
        frappe.db.set_single_value(
            'Website Settings', 'home_page', new_home_route)

        frappe.db.commit()

    home_route = "go1-landing"
    update_home_page(home_route)

    insert_custom_fields(theme, nodata)
    clear_cache_for_current_site()
    return 'success'


# @frappe.whitelist(allow_guest=True)
def clear_cache_for_current_site():
    """ CLear Cache """

    current_site = frappe.local.site
    commands = f"bench --site {current_site} clear-cache"
    os.system(commands)
    return commands


@frappe.whitelist(allow_guest=True)
def prepend_domain_to_image_urls(data, domain):
    """Recursively prepend domain to image URLs in the given dictionary or list."""

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str) and value.startswith("/files/"):
                data[key] = domain + value
                log_message = f"Updated URL for key {key}: {data[key]}"
            elif isinstance(value, (dict, list)):
                prepend_domain_to_image_urls(value, domain)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                prepend_domain_to_image_urls(item, domain)


def update_blocks_with_domain(blocks, domain):
    """Update the blocks key with domain prepended to all src attributes."""

    try:
        blocks_data = json.loads(blocks)
        prepend_domain_to_image_urls(blocks_data, domain)
        return json.dumps(blocks_data)
    except json.JSONDecodeError as e:
        frappe.log_error(frappe.get_traceback(),
                         "JSON Decode Error in update_blocks_with_domain")
        return blocks


@frappe.whitelist()
def truncate_message(message):
    """Truncate message to fit the maximum allowed length."""
    return message


def log_error_message(message, title):
    """Log error message in parts if it exceeds the max length."""
    frappe.log_error(message, title)


def get_uploaded_file_content(filedata):
    try:
        import base64
        if filedata:
            if "," in filedata:
                filedata = filedata.rsplit(",", 1)[1]
            uploaded_content = base64.b64decode(filedata)
            return uploaded_content
        else:
            frappe.msgprint(_('No file attached'))
            return None
    except Exception as e:
        frappe.log_error(
            "Error in seapi.get_uploaded_file_content", frappe.get_traceback())


@frappe.whitelist(allow_guest=True)
def insert_custom_fields(theme, nodata=None):
    """
    Inserts custom fields and related configurations for the Go1 Webshop Theme.

    Args:
        theme (str): The theme name to fetch data for.
        nodata (int, optional): A flag to skip processing specific data types.
    """
    import requests
    import os
    import shutil
    import zipfile
    from urllib.request import urlopen
    import tempfile

    def log_error_custom(title, message):
        """
        Helper function to log errors with truncated titles.

        Args:
            title (str): Error title.
            message (str): Full error message or traceback.
        """
        title = title[:140] if len(title) > 140 else title
        frappe.log_error(message, title)

    print("[INFO] Initializing Go1 Webshop Theme Custom Fields Insertion")

    # Fetch Webshop Theme Settings from Frappe configuration
    webshop_theme_settings = frappe.get_single("Go1 Webshop Theme Settings")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"token {webshop_theme_settings.api_key}:{webshop_theme_settings.api_secret}"
    }

    # URL to fetch theme data from the external system
    external_url = f"{webshop_theme_settings.url}/api/method/go1_webshop_theme.go1_webshop_theme.utils.get_all_json"

    try:
        print("[INFO] Fetching theme data from external API")
        # Make API request to fetch theme data
        response = requests.get(
            external_url, headers=headers, json={"theme": theme})
        response.raise_for_status()

        # Parse the response JSON
        themes = response.json()
        message = themes.get("message", [])
        print("[INFO] Theme data fetched successfully")

        for row in message:
            for i, j in row.items():
                if i == "file_list":
                    print("[INFO] Processing file list")
                    # Use a temporary directory to handle downloaded files
                    with tempfile.TemporaryDirectory() as temp_dir:
                        file_path = os.path.join(
                            temp_dir, "go1_webshop_files.zip")

                        try:
                            # Download the file list from the URL
                            print("[INFO] Downloading file list")
                            with urlopen(j) as data, open(file_path, 'wb') as zip_ref:
                                shutil.copyfileobj(data, zip_ref)

                            # Extract the ZIP file contents
                            print("[INFO] Extracting files")
                            with zipfile.ZipFile(file_path, 'r') as file_data:
                                for file in file_data.infolist():
                                    # Skip directories and system files
                                    if file.is_dir() or file.filename.startswith("__MACOSX/"):
                                        continue
                                    filename = os.path.basename(file.filename)
                                    if filename.startswith("."):
                                        continue

                                    # Determine file path in the system
                                    origin = get_files_path()
                                    item_file_path = os.path.join(
                                        origin, file.filename)

                                    # Check if the file already exists in the database
                                    if not frappe.db.exists("File", {"file_name": filename}):
                                        print(
                                            f"[INFO] File does not exist in the database, uploading: {filename}")
                                    else:
                                        print(
                                            f"[INFO] File exists in the database, cleaning up: {filename}")

                                        # Handle cleanup of existing file versions
                                        base_filename, ext = os.path.splitext(
                                            filename)
                                        existing_files = frappe.db.get_list(
                                            "File",
                                            filters={"file_name": [
                                                "like", f"{base_filename}%{ext}"]},
                                            fields=["name", "file_url"]
                                        )
                                        for existing_file in existing_files:
                                            try:
                                                existing_file_path = frappe.utils.get_files_path(
                                                    existing_file["file_url"])
                                                if os.path.exists(existing_file_path):
                                                    os.remove(
                                                        existing_file_path)
                                                # Delete the file record from the database
                                                frappe.delete_doc(
                                                    "File", existing_file["name"], force=True)
                                            except frappe.PermissionError as e:
                                                log_error_custom(
                                                    "Failed to remove file", str(e))
                                            except Exception as cleanup_error:
                                                log_error_custom(
                                                    "File cleanup error",
                                                    f"Failed to remove {existing_file_path}: {str(cleanup_error)}"
                                                )

                                    # Upload the new file to the system
                                    try:
                                        file_doc = frappe.new_doc("File")
                                        file_doc.content = file_data.read(
                                            file.filename)
                                        file_doc.file_name = filename
                                        file_doc.folder = "Home"
                                        file_doc.is_private = 0
                                        file_doc.save(ignore_permissions=True)

                                        saved_path = frappe.utils.get_files_path(
                                            file_doc.file_url)
                                        print(
                                            f"[INFO] File uploaded successfully: {saved_path}")
                                    except Exception as e:
                                        log_error_custom(
                                            "File upload error", f"Failed to upload file: {filename}, Error: {str(e)}")

                        except Exception as e:
                            # Log errors during file list processing
                            log_error_custom(
                                "File list processing error", frappe.get_traceback())
                            continue

                try:
                    # Process and insert JSON data into the system
                    if isinstance(j, dict):
                        # Insert specific doctypes only if they don't already exist
                        if j['doctype'] == "Go1 Webshop Theme" and not frappe.db.exists({"doctype": j['doctype'], "name": j['name']}):
                            frappe.get_doc(j).insert(
                                ignore_permissions=True, ignore_mandatory=True)
                        if j['doctype'] == "Builder Settings":
                            frappe.get_doc(j).insert(
                                ignore_permissions=True, ignore_mandatory=True)

                    # Handle lists of records
                    if isinstance(j, list):
                        for k in j:
                            # Skip specific doctypes if `nodata` is enabled
                            if nodata != 1 or k['doctype'] not in ["Item Group", "Item", "Website Item"]:
                                # Handle various doctypes based on conditions
                                if k['doctype'] == "Builder Component":
                                    create_builder_component(k)
                                elif k['doctype'] == "Builder Client Script" and not frappe.db.exists({"doctype": k.get('doctype'), "name": k.get('name')}):
                                    script_doc = frappe.get_doc(k).insert(
                                        ignore_permissions=True, ignore_mandatory=True)
                                    frappe.db.sql("""UPDATE `tabBuilder Client Script` SET name=%(c_name)s WHERE name=%(s_name)s""", {
                                        "c_name": k.get('name'), "s_name": script_doc.name})
                                    frappe.db.commit()
                                elif k['doctype'] == "Custom Field" and not frappe.db.exists({"doctype": k['doctype'], "name": k['name']}):
                                    frappe.get_doc(k).insert(
                                        ignore_permissions=True, ignore_mandatory=True)
                                elif k['doctype'] == "Item Group" and not frappe.db.exists({"doctype": k['doctype'], "name": k['item_group_name']}):
                                    frappe.get_doc(k).insert(
                                        ignore_permissions=True, ignore_mandatory=True)
                                elif k['doctype'] == "Mobile Menu" and not frappe.db.exists({"doctype": k['doctype'], "name": k['name']}):
                                    frappe.get_doc(k).insert(
                                        ignore_permissions=True, ignore_mandatory=True)
                                elif k['doctype'] == "Website Slideshow" and not frappe.db.exists({"doctype": k['doctype'], "name": k['slideshow_name']}):
                                    frappe.get_doc(k).insert(
                                        ignore_permissions=True, ignore_mandatory=True)
                                elif k['doctype'] == "Item" and not frappe.db.exists({"doctype": k['doctype'], "name": k['name']}):
                                    insert_item_data(j)
                                elif k['doctype'] == "Website Item" and not frappe.db.exists({"doctype": k['doctype'], "name": k['name']}):
                                    insert_item_data(j)
                                elif k['doctype'] == "Builder Page":
                                    read_page_module_path(j)
                except Exception as e:
                    # Log errors during JSON data processing
                    log_error_custom(
                        "Insert custom fields error", frappe.get_traceback())
    except Exception as e:
        # Log top-level errors
        log_error_custom("Insert custom fields exception",
                         frappe.get_traceback())


def create_builder_component(param):
    try:
        if not frappe.db.exists({"doctype": param['doctype'], "name": param['component_id']}):
            frappe.get_doc(param).insert(
                ignore_permissions=True, ignore_mandatory=True)
        else:
            doc = frappe.get_doc(param['doctype'], param['component_id'])
            doc.unlock()
            doc.update(param)
            doc.save(ignore_permissions=True, ignore_mandatory=True)
        frappe.db.commit()
    except frappe.exceptions.DocumentLockedError:
        frappe.log_error("frappe.exceptions.DocumentLockedError",
                         frappe.get_traceback())
        pass
    except Exception as e:
        frappe.log_error("create_builder_component_error",
                         frappe.get_traceback())


def read_page_module_path(out):
    out_json = {}
    for index, i in enumerate(out):
        try:

            if i.get('client_scripts'):
                out_json[i.get('page_title')] = i['client_scripts']
                del i['client_scripts']
            if not frappe.db.exists({"doctype": i.get('doctype'), "page_title": i.get('page_title')}):

                page_doc = frappe.get_doc(i).insert(
                    ignore_permissions=True, ignore_mandatory=True)

                frappe.db.set_single_value(
                    i.get('doctype'), 'route', i.get('route'))

                if i.get('page_title') in out_json:
                    for child_index, script in enumerate(out_json[i.get('page_title')]):
                        script_name = f"{script.get('builder_script')}{page_doc.name}{child_index}"

                        frappe.db.sql(f"""INSERT INTO `tabBuilder Page Client Script` (name, builder_script, parent, parentfield, parenttype)
                            VALUES (%s, %s, %s, 'client_scripts', 'Builder Page')""",
                                      (script_name, script.get('builder_script'), page_doc.name))

                        frappe.db.commit()
            else:
                page_doc = frappe.get_doc(
                    i.get('doctype'), {"page_title": i.get('page_title')})
                # if i["name"]:
                #     del i["name"]
                page_doc.update(i)
                page_doc.save(ignore_permissions=True)

        except Exception as e:
            frappe.log_error("read_page_module_path", frappe.get_traceback())
    for page in out:
        if page.get('page_title') == "Go1 Landing":
            frappe.db.set_single_value(
                "Website Settings", "home_page", page.get('route'))


@frappe.whitelist(allow_guest=True)
def insert_item_data(out):
    item_codes = []
    warehouse = None
    max_log_length = 140

    for i in out:
        try:
            if not frappe.db.exists({"doctype": i.get('doctype'), "item_name": i.get('item_name')}):
                if i.get('doctype') == "Website Item":
                    company = frappe.db.get_all("Company", fields=['abbr'])
                    if company:
                        i["website_warehouse"] = "Stores - " + company[0].abbr
                        warehouse = "Stores - " + company[0].abbr

                if "india_compliance" in frappe.get_installed_apps() and i.get('doctype') == "Item":
                    i["gst_hsn_code"] = "999900"

                frappe.get_doc(i).insert(
                    ignore_permissions=True, ignore_mandatory=True)

                if i.get('doctype') == "Website Item":
                    price_doc = frappe.new_doc("Item Price")
                    price_doc.item_code = i.get("item_code")
                    price_doc.price_list = "Standard Selling"
                    price_doc.selling = 1
                    price_doc.price_list_rate = 5000
                    price_doc.is_go1_webshop_item = 1

                    # Check if the item exists before saving the price
                    if frappe.db.exists("Item", price_doc.item_code):
                        price_doc.save(ignore_permissions=True)
                        item_codes.append(i.get("item_code"))
                    else:
                        frappe.log_error(
                            f"Item {price_doc.item_code} not found. Skipping price insertion.")

        except frappe.NameError:
            pass
        except Exception as e:
            error_message = frappe.get_traceback()
            frappe.log_error(error_message, "insert_item_data_error")
