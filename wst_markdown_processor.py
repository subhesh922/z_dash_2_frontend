import re 

import re

class Wst_MarkdownExtractor:
    def __init__(self, markdown_text: str):
        self.markdown_text = markdown_text

        # Headings for noisy (old) format
        self.table_headings_noisy = [
            "### 🧩 Release Scope Metrics (Epics, PIRs)",
            "### 📦 SFDC Defects Fixed",
            "### 📊 Critical Release Metrics"
        ]

        self.section_headings_noisy = [
            "**Key Stakeholders:**",
            "**Critical Release Metrics:**",
            "**Release Health Trends:**"
        ]

        # Headings for clean (new) format
        self.clean_headings = [
            "## 📦 Release Scope",
            "## 👥 Key Stakeholders",
            "## 📊 Critical Release Metrics",
            "## 📈 Release Health Trends"
        ]

    def extract(self):
        if "## 📦 Release Scope" in self.markdown_text:
            return self._extract_clean_format()
        else:
            return self._extract_noisy_format()

    def _extract_clean_format(self):
        combined_text = ""
        for heading in self.clean_headings:
            pattern = rf"{re.escape(heading)}\s*\n([\s\S]*?)(?=\n## |\Z)"
            match = re.search(pattern, self.markdown_text)
            section = match.group(1).strip() if match else "*Section Not Found*"
            combined_text += f"{heading}\n{section}\n\n"
        return combined_text

    def _extract_noisy_format(self):
        combined_text = ""

        # Process noisy tables
        for heading in self.table_headings_noisy:
            section = self._extract_section_noisy(self.markdown_text, heading)
            combined_text += f"{heading}\n{section}\n\n"

        # Process complex noisy sections
        for heading in self.section_headings_noisy:
            section = self._extract_section_noisy(self.markdown_text, heading)

            if heading == "**Key Stakeholders:**" and section != "*Section Not Found*":
                section = self._preprocess_key_stakeholders(section)
            elif heading == "**Critical Release Metrics:**" and section != "*Section Not Found*":
                section = self._preprocess_critical_release_metrics(section)
            elif heading == "**Release Health Trends:**" and section != "*Section Not Found*":
                section = self._preprocess_release_health_trends(section)

            heading_norm = f"### {heading.replace('**','').replace(':','').strip()}"
            combined_text += f"{heading_norm}\n{section}\n\n"

        return combined_text

    def _extract_section_noisy(self, markdown_text, section_heading):
        if section_heading.startswith("**"):
            pattern = rf"{re.escape(section_heading)}\n[-]+\n([\s\S]*?)(?=\n\*\*.*?:\n[-]+|\Z)"
        else:
            pattern = rf"{re.escape(section_heading)}\s*([\s\S]*?)(?=\n## |\n### |\n\*\*|\Z)"
        match = re.search(pattern, markdown_text)
        return match.group(1).strip() if match else "*Section Not Found*"

    def _preprocess_key_stakeholders(self, section_text):
        parts = re.split(r"\n+(Functional Group|Approver|Functional Lead)\n+", section_text)
        if len(parts) < 5: return section_text
        fg_block, approver_block, lead_block = parts[0], parts[2], parts[4]
        fg = [re.sub(r"^\*\*|\*\*$", "", line.strip()) for line in fg_block.split("\n") if line.strip()]
        approvers = [line.strip() for line in approver_block.split("\n") if line.strip()]
        leads = [line.strip() for line in lead_block.split("\n") if line.strip()]
        min_len = min(len(fg), len(approvers), len(leads))
        table = "| Functional Group | Approver | Functional Lead |\n|---|---|---|\n"
        for i in range(min_len):
            table += f"| {fg[i]} | {approvers[i]} | {leads[i]} |\n"
        return table

    def _preprocess_critical_release_metrics(self, section_text):
        items = re.split(r"\n\*\*(\d+)\*\*\n", section_text)
        header = "| Item No | Metric | Release Criteria | Result | Risk Status | Summary |\n|---|---|---|---|---|---|\n"
        table_rows = ""
        for i in range(1, len(items), 2):
            item_no, block = items[i], items[i+1].strip()
            fields = [line.strip() for line in block.split("\n") if line.strip()]
            row = [fields[j] if j < len(fields) else "" for j in range(5)]
            table_rows += f"| {item_no} | {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} |\n"
        return header + table_rows

    def _preprocess_release_health_trends(self, section_text):
        items = re.split(r"\n\*\*(\d+)\*\*\n", section_text)
        header = "| Item No | Metric | Release Criteria | Previous Release | Current Release | Status | Summary |\n|---|---|---|---|---|---|---|\n"
        table_rows = ""
        for i in range(1, len(items), 2):
            item_no, block = items[i], items[i+1].strip()
            fields = [line.strip() for line in block.split("\n") if line.strip()]
            row = [fields[j] if j < len(fields) else "" for j in range(6)]
            table_rows += f"| {item_no} | {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]} |\n"
        return header + table_rows


class Wst_MarkdownHarmonizer:
    def __init__(self):
        pass

    def harmonize(self, version_to_extracted_md: dict) -> str:
        sections = {
            "release_scope": {},
            "critical_metrics": {},
            "health_trends": {},
            "key_stakeholders": {}
        }

        for version, md_text in version_to_extracted_md.items():
            release_scope_section = self._extract_section(md_text, ["## 📦 Release Scope", "### 🧩 Release Scope Metrics (Epics, PIRs)"])
            release_scope_section = self._add_table_headers_if_missing(release_scope_section, "Release Scope")
            sections["release_scope"][version] = release_scope_section

            critical_section = self._extract_section(md_text, [
                "## 📊 Critical Release Metrics", 
                "### 📊 Critical Release Metrics", 
                "### Critical Release Metrics"
            ])
            critical_section = self._add_table_headers_if_missing(critical_section, "Critical Metrics")
            sections["critical_metrics"][version] = critical_section

            health_trends_section = self._extract_section(md_text, [
                "## 📈 Release Health Trends", 
                "### Release Health Trends", 
                "**Release Health Trends:**"
            ])
            health_trends_section = self._add_table_headers_if_missing(health_trends_section, "Health Trends")
            sections["health_trends"][version] = health_trends_section

            sections["key_stakeholders"][version] = self._extract_section(md_text, [
                "## 👥 Key Stakeholders", 
                "### Key Stakeholders", 
                "**Key Stakeholders:**"
            ])

        combined_markdown = ""

        combined_markdown += "## 📦 Release Scope\n"
        for version in sorted(sections["release_scope"].keys()):
            combined_markdown += f"\n### Version {version}\n"
            combined_markdown += sections["release_scope"][version] + "\n"

        combined_markdown += "\n## 📊 Critical Release Metrics\n"
        for version in sorted(sections["critical_metrics"].keys()):
            combined_markdown += f"\n### Version {version}\n"
            combined_markdown += sections["critical_metrics"][version] + "\n"

        combined_markdown += "\n## 📈 Release Health Trends\n"
        for version in sorted(sections["health_trends"].keys()):
            combined_markdown += f"\n### Version {version}\n"
            combined_markdown += sections["health_trends"][version] + "\n"

        combined_markdown += "\n## 👥 Key Stakeholders\n"
        for version in sorted(sections["key_stakeholders"].keys()):
            combined_markdown += f"\n### Version {version}\n"
            combined_markdown += sections["key_stakeholders"][version] + "\n"

        return combined_markdown.strip()

    def _extract_section(self, markdown_text, heading_candidates):
        for heading in heading_candidates:
            pattern = rf"{re.escape(heading)}\s*\n([\s\S]*?)(?=\n## |\n### |\Z)"
            match = re.search(pattern, markdown_text)
            if match:
                return match.group(1).strip()
        return "*Section Not Found*"

    def _add_table_headers_if_missing(self, text: str, section: str) -> str:
        if text.strip() == "*Section Not Found*":
            return text

        lines = text.strip().split("\n")
        if len(lines) < 2:
            return text  # Not enough lines to be a table

        # If the table already has a header row (pipes and separator), do nothing
        if "|" in lines[0] and "---" in lines[1]:
            return text

        # Inject fallback headers based on section
        if section == "Release Scope":
            header = "| Scope Item | Total | Open | Comments |\n|------------|-------|------|----------|"
        elif section == "SFDC Defects":
            header = "| ATL | BTL | Total | Comments |\n|-----|-----|-------|----------|"
        elif section == "Health Trends":
            header = "| Metric | Criteria | Previous | Current | Status | Summary |\n|--------|----------|----------|---------|--------|---------|"
        elif section == "Critical Metrics":
            header = "| Functional Group | Type | Total | Open | Risk Status | Comments |\n|------------------|------|-------|------|-------------|----------|"
        else:
            return text

        return header + "\n" + text

