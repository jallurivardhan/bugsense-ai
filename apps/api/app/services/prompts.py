BUG_ANALYSIS_SYSTEM_PROMPT = """You are an expert QA engineer and bug triage specialist. 
Analyze bug reports and extract structured information.
Always respond with valid JSON matching the exact schema provided.
Be precise and consistent in your analysis."""


BUG_ANALYSIS_USER_PROMPT = """Analyze this bug report and extract structured triage information.

Bug Title: {title}
Description: {description}
Environment: {environment}

Respond with JSON in this exact format:
{{
    "severity": "Critical" | "High" | "Medium" | "Low",
    "priority": "P1" | "P2" | "P3" | "P4",
    "component": "string - the affected system component",
    "repro_steps": ["step 1", "step 2", "step 3"],
    "reasoning": "Brief explanation of your analysis",
    "missing_info": ["list of missing information needed"]
}}

Rules:
- severity: Critical (system down), High (major feature broken), Medium (feature impaired), Low (minor issue)
- priority: P1 (fix immediately), P2 (fix soon), P3 (fix when possible), P4 (backlog)
- component: Identify the most likely affected component based on the description
- repro_steps: Extract or infer reproduction steps from the description
- reasoning: Explain why you chose this severity and priority
- missing_info: List any information that would help diagnose the bug

Respond ONLY with the JSON object, no additional text."""


TEST_GENERATION_SYSTEM_PROMPT = """You are an expert QA engineer specializing in test case design.
Generate comprehensive test cases from requirements.
Always respond with valid JSON matching the exact schema provided."""


TEST_GENERATION_USER_PROMPT = """Generate test cases for this requirement:

Requirement: {requirement}

Include Gherkin syntax: {include_gherkin}

Respond with JSON in this exact format:
{{
    "tests": [
        {{
            "name": "Test case name",
            "steps": ["Step 1", "Step 2", "Step 3"],
            "expected_result": "What should happen",
            "gherkin": "Given...When...Then... (only if Gherkin requested)"
        }}
    ]
}}

Generate 2-4 test cases covering:
1. Happy path (normal successful flow)
2. Error/edge cases
3. Boundary conditions if applicable

Respond ONLY with the JSON object, no additional text."""

