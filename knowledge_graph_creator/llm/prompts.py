EXTRACT_PROMPT = """
You are an expert scientific literature analyst. Your task is to identify semantic relationships between two research papers by carefully analyzing their abstracts.

**Paper 1 (Source Paper):**
Title: {source_title}
Abstract: {source_abstract}

**Paper 2 (Target Paper):**
Title: {target_title}
Abstract: {target_abstract}

**Task:**
Analyze the relationship between Paper 1 and Paper 2. Identify if Paper 1 has any of the following semantic relationships with Paper 2. Multiple relationships may exist simultaneously.

**Relationship Types:**

1. **Extends**: Paper 1 builds upon, extends, or improves the methodology, framework, or approach presented in Paper 2.

2. **Solves**: Paper 1 addresses a problem, limitation, or challenge that was identified or left unsolved in Paper 2.

3. **Outperforms**: Paper 1 reports better performance, results, or metrics compared to the method/approach in Paper 2.

4. **Validates**: Paper 1 confirms, verifies, or provides supporting evidence for the findings, claims, or methods in Paper 2.

5. **Contradicts**: Paper 1 presents findings, results, or conclusions that conflict with or challenge those in Paper 2.

6. **Requires**: Paper 1 depends on, uses as a prerequisite, or builds directly upon concepts/methods from Paper 2 as a necessary foundation.

7. **Enables**: Paper 2 provides tools, frameworks, datasets, or methodologies that make Paper 1's work possible.

8. **Adapts-from**: Paper 1 modifies or applies the approach from Paper 2 to a different domain, problem, or context.

9. **Achieves**: Paper 1 successfully implements or realizes a goal, objective, or application suggested in Paper 2.

10. **Challenges**: Paper 1 questions the assumptions, methodology, or validity of Paper 2 without necessarily contradicting its results.

**Instructions:**
1. Read both abstracts carefully and consider their content jointly
2. Identify ALL applicable relationships (there may be 0, 1, or multiple relationships)
3. For each identified relationship, provide specific evidence from the abstracts
4. Be precise and only identify relationships that are clearly supported by the text

**Output Format (JSON):**
Return your analysis as a valid JSON object with the following structure:

{{
  "relationships": [
    {{
      "type": "relationship_type_name",
      "confidence": "high|medium|low",
      "evidence": "Specific text or reasoning from the abstracts supporting this relationship",
      "explanation": "Brief explanation of why this relationship exists"
    }}
  ],
  "no_relationship_reason": "If no relationships found, explain why"
}}

**Example Output:**
{{
  "relationships": [
    {{
      "type": "Extends",
      "confidence": "high",
      "evidence": "Paper 1 mentions 'building upon the transformer architecture' while Paper 2 introduces 'the transformer model'",
      "explanation": "Paper 1 explicitly extends the methodology introduced in Paper 2"
    }},
    {{
      "type": "Outperforms",
      "confidence": "medium",
      "evidence": "Paper 1 reports '95% accuracy' while Paper 2 achieved '87% accuracy' on similar tasks",
      "explanation": "Paper 1 demonstrates superior performance on comparable benchmarks"
    }}
  ]
}}

Now analyze the relationship between the two papers provided above and return your response in the specified JSON format.
"""

RELATIONSHIP_PROMPT_COT = """
You are an expert analyst examining **citation relationships** in a **scientific knowledge graph**.  
Your goal is to determine how a **citing paper** semantically relates to a **cited paper**, using their titles and abstracts.


## INPUT

### CITING PAPER
- **Title:** {citing_title}  
- **Abstract:** {citing_abstract}

### CITED PAPER
- **Title:** {cited_title}  
- **Abstract:** {cited_abstract}

## TASK (Reason Step-by-Step Internally)

1. Identify the **core contribution** of the cited paper (problem, method, findings).
2. Identify the **main contribution and intent** of the citing paper.
3. Compare both papers to understand how the citing paper:
   - uses,
   - builds upon,
   - evaluates,
   - adapts,
   - challenges, or
   - depends on  
   the cited work.
4. Select the **single PRIMARY semantic relationship** that best describes this citation.


## RELATIONSHIP TYPES (Choose Exactly One)

1. **Extends** – Citing paper builds upon or extends methods/framework from cited paper  
2. **Solves** – Citing paper solves a problem identified in cited paper  
3. **Outperforms** – Citing paper demonstrates better performance than cited paper  
4. **Validates** – Citing paper validates or confirms findings from cited paper  
5. **Contradicts** – Citing paper contradicts or challenges cited paper’s conclusions  
6. **Requires** – Citing paper requires concepts/methods from cited paper as a foundation  
7. **Enables** – Cited paper’s work enables the citing paper’s approach  
8. **Adapts-from** – Citing paper adapts techniques from cited paper to a new context  
9. **Achieves** – Citing paper achieves goals or addresses challenges stated in cited paper  
10. **Challenges** – Citing paper questions assumptions or limitations in cited paper  


## OUTPUT FORMAT (Respond EXACTLY in this JSON)

```json
{
  "relationship": "one of the 10 types above",
  "confidence": "high | medium | low",
  "evidence": "brief quote or paraphrase from the citing abstract supporting this"
}
"""
