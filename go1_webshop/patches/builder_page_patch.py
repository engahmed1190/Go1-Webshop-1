from builder.builder.doctype.builder_page.builder_page import BuilderPage
from go1_webshop.go1_webshop.doctype.go1_webshop_theme.go1_webshop_theme import (
    get_css_content,
    get_curnet_doc,
)
import frappe
from jinja2.exceptions import TemplateSyntaxError
from frappe.utils.jinja import render_template


def execute():
    """
    Patch entry point for Frappe. Ensure it's callable.
    """
    try:
        # Apply the patch
        BuilderPage.get_context = custom_get_context
        frappe.log_error("BuilderPage patched successfully", "Patch Execution")
    except Exception as e:
        frappe.log_error(str(e), "Patch Execution Error")


def custom_get_context(self, context):
    """
    Custom implementation for get_context to inject additional CSS.
    """
    # Default Favicon Handling
    if hasattr(context, "favicon"):
        del context.favicon

    context.disable_indexing = self.disable_indexing

    # Fetch page data
    page_data = self.get_page_data()
    if page_data.get("title"):
        context.title = page_data.get("page_title")

    # Handle dynamic blocks and preview
    blocks = self.blocks
    context.preview = frappe.flags.show_preview

    if self.dynamic_route or page_data:
        context.no_cache = 1

    if frappe.flags.show_preview and self.draft_blocks:
        blocks = self.draft_blocks

    # Fetch and inject custom CSS
    css_content = ""
    try:
        webshop_settings = frappe.db.get_value(
            "Go1 Webshop Settings", "Go1 Webshop Settings", "selected_theme"
        )
        if webshop_settings:
            webshop_theme = get_curnet_doc(webshop_settings)
            if webshop_theme:
                css_content = get_css_content(webshop_settings)
                context.style = context.get(
                    "style", "") + f"<style>{css_content}</style>"
                frappe.log_error(
                    "Custom CSS successfully injected", "CSS Injection")
    except Exception as e:
        frappe.log_error(str(e), "Custom CSS Fetch Error")

    # Editor link
    context.editor_link = f"/builder/page/{self.name}"

    # Base URL handling
    if self.dynamic_route and hasattr(frappe.local, "request"):
        context.base_url = frappe.utils.get_url(
            frappe.local.request.path or self.route)
    else:
        context.base_url = frappe.utils.get_url(self.route)

    # Add scripts and styles
    self.set_style_and_script(context)

    # Update context with page data
    context.update(page_data)

    # Set meta tags
    self.set_meta_tags(context=context, page_data=page_data)

    # Favicon management
    self.set_favicon(context)

    # Render template content
    try:
        context["content"] = render_template(context.content, context)
    except TemplateSyntaxError as e:
        frappe.log_error(str(e), "Template Syntax Error")
        raise
