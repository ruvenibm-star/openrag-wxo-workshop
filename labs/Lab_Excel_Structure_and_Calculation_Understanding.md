# Lab: Explore Excel Structure and Calculation Context with OpenRAG

## Objective

In this lab, you will upload two Excel workbooks and use OpenRAG to retrieve information represented through:

- Vertically merged cells
- Horizontally merged headings
- Formula-based calculations
- Described calculation logic associated with macro-generated values

## Files Used

Upload the following files:

1. `Operational_Readiness_Plan.xlsx`
   - Contains operational phases, responsible units, schedules, readiness statuses, dependencies, and coordination directives.
   - Uses merged cells to represent relationships across multiple rows and columns.

2. `Operational_Cost_Model.xlsx`
   - Contains quantities, unit costs, contingency rates, formula-calculated totals, and macro-output values.
   - Includes supporting calculation context within the workbook.

## Step 1: Upload the Excel Files

1. Open the OpenRAG interface.
2. Go to the document upload or ingestion area.
3. Upload `Operational_Readiness_Plan.xlsx`.
4. Upload `Operational_Cost_Model.xlsx`.
5. Confirm that both files have completed processing before continuing.

## Step 2: Test Merged-Cell Understanding

Ask the following questions one at a time.

### Question 1

> Which units belong to Phase 1 — Mobilisation, and what is the readiness status of each?

This tests whether OpenRAG correctly associates each responsible unit with a phase name that spans multiple rows.

### Question 2

> Under the Schedule heading, when does Network Operations start and complete its task?

This tests whether OpenRAG understands the relationship between a merged group heading and the Start and Complete subheadings beneath it.

### Question 3

> List every At Risk activity, including its phase, responsible unit, completion date and critical dependency.

This tests whether OpenRAG can combine information across multiple columns while preserving the correct phase-to-unit relationships.

## Step 3: Test Calculation Understanding

Ask the following questions one at a time.

### Question 4

> What formula is used to calculate the Formula Total for Secure field laptops? Explain the calculation and the inputs used.

This tests whether OpenRAG can retrieve the formula and relate it to the relevant quantity, unit cost, and contingency rate.

### Question 5

> How was the Macro Output for Secure field laptops calculated?

This tests whether OpenRAG can retrieve the calculation context provided within the workbook and explain how the output value was derived.

## Step 4: Review the Responses

For each answer, verify that OpenRAG:

- Associates units with the correct operational phase.
- Interprets the Start and Complete columns under the Schedule heading correctly.
- Keeps readiness status and dependency information linked to the correct unit.
- Identifies the formula and input values used for the Formula Total.
- Explains the calculation method used for the Macro Output.

## Expected Outcome

OpenRAG should retrieve information from both workbooks while preserving the relationships expressed through spreadsheet structure. The responses should demonstrate that information can be retrieved not only from individual cells, but also from the surrounding headings, merged-cell groupings, formulas, and calculation context.
