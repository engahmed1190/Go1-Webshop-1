from builder.builder.doctype.builder_page.builder_page import BuilderPage
from go1_webshop.go1_webshop.doctype.go1_webshop_theme.go1_webshop_theme import (
    get_css_content,
    get_curnet_doc,
)
import frappe


def execute():
    """
    Patch entry point for Frappe. Ensure it's callable.
    """
    try:
        # Apply the patch
        from builder.builder.doctype.builder_page.builder_page import BuilderPage
        BuilderPage.get_context = custom_get_context
        frappe.log_error("BuilderPage patched successfully", "Patch Execution")
    except Exception as e:
        frappe.log_error(str(e), "Patch Execution Error")


def custom_get_context(self, context):
    """
    Custom implementation for get_context to inject additional CSS.
    """
    # Call the original implementation
    if hasattr(BuilderPage, "get_context"):
        original_get_context = BuilderPage.get_context
        original_get_context(self, context)

    # Add custom CSS logic
    try:
        webshop_settings = frappe.db.get_value(
            "Go1 Webshop Settings", "Go1 Webshop Settings", "selected_theme"
        )
        if webshop_settings:
            webshop_theme = get_curnet_doc(webshop_settings)
            if webshop_theme:
                css_content = get_css_content(webshop_settings)
                context.style += f"<style>{css_content}</style>"

        frappe.log_error("Custom CSS successfully injected",
                         "BuilderPage Patch")

    except Exception as e:
        frappe.log_error(message=str(e), title="Custom BuilderPage Error")
