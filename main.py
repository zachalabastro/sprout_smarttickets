# Install Dependencies
import os
import time
import streamlit as st
import ast
import pandas as pd
import pytesseract
import PyPDF2
from PIL import Image
from openai import AzureOpenAI
from st_copy_to_clipboard import st_copy_to_clipboard

os.system('clear')

# Load file upload folder
upload_dir = "file_upload" # Replace accordingly
output_dir = "file_output" # Replace accordingly
output_file = "file_output/final_output.txt" # Replace accordingly
os.makedirs(upload_dir, exist_ok=True)

# Initial deletes to avoid token maximum capacity --
# Delete uploaded files
files = os.listdir(upload_dir)
for file in files:
        os.remove(os.path.join(upload_dir, file))

# Delete output files
outputs = os.listdir(output_dir)
for output in outputs:
    os.remove(os.path.join(output_dir, output))

# Load Dataset labels
df_full = pd.read_csv("dependencies/CA_full.csv") # To provide the LLM with the tag options
type = df_full['Ticket Type'].unique()
print(type)
priority = df_full['Ticket Priority'].unique()
print(priority)
module = df_full['Module'].unique()
print(module)
product = df_full['Product'].unique()
print(product)

# Azure OpenAI Key
client = AzureOpenAI(
  api_key = os.getenv("AZURE_OPENAI_KEY"),  
  api_version = "2024-02-01",
  azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
)

# Define the Streamlit app layout
def main():
    st.title('Customer Advocacy SmartTickets')

    # Form input
    with st.form(key='my_form'):
        st.header('Submit a Ticket')
        st.markdown("<hr>", unsafe_allow_html=True)

        # Text input
        # File uploads
        subject_type = st.text_input('Subject Type', max_chars=100)
        ticket_body = st.text_area('Ticket Body', height=150)   
        uploaded_files = st.file_uploader('Upload Screenshots', type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        
        # Upload file button (not a requirement)
        upload_file_button = st.form_submit_button(label='Upload Files')

        # Upload the files selected
        if upload_file_button:
            # Reoccuring deletes whenever new data/files are given --
            # Delete uploaded files
            files = os.listdir(upload_dir)
            for file in files:
                    os.remove(os.path.join(upload_dir, file))

            # Delete output files
            outputs = os.listdir(output_dir)
            for output in outputs:
                os.remove(os.path.join(output_dir, output))

            # Upload completion
            if not uploaded_files:
                st.warning("No files were selected. Please select at least one file.")
            else:
                with st.spinner('Uploading Files...'):
                    for uploaded_file in uploaded_files:
                        with open(os.path.join(upload_dir, uploaded_file.name), "wb") as f:
                            f.write(uploaded_file.read())

                    # Process each uploaded image or PDF file
                    for i, uploaded_file in enumerate(uploaded_files, start=1):
                        for filename in os.listdir(upload_dir):
                            if filename.endswith('.jpg') or filename.endswith('.jpeg'):
                                
                                # Extract text from image
                                with Image.open(uploaded_file) as img:
                                    text = pytesseract.image_to_string(img)
                                
                                # Save extracted text
                                with open(f'file_output/upload_text_{i}.txt', 'w') as file:
                                    file.write(text)

                            elif filename.endswith('.pdf'):
                                pdf_file = open(uploaded_file, 'rb')
                                pdf_reader = PyPDF2.PdfReader(pdf_file)

                                # Save extracted text
                                with open(f'file_output/upload_text_{i}.txt', 'w') as file:
                                    for page_num in range(len(pdf_reader.pages)):
                                        page = pdf_reader.pages[page_num]
                                        file.write(page.extract_text())
                    time.sleep(5)
                st.success(f"All files have been uploaded successfully.")

        # Please each .txt (context) into one main .txt file
        with open(output_file, 'a') as output:
            for filename in os.listdir(output_dir):
                if filename.endswith('.txt'):
                    with open(os.path.join(output_dir, filename), 'r') as file:
                        file_contents = file.read()
                output.write(file_contents + '\n---\n')
        with open(output_file, 'r') as context:
            global screenshot_text
            screenshot_text = context.read()

        st.markdown("<hr>", unsafe_allow_html=True)

        # Initializing text classification
        submit_button = st.form_submit_button(label='Generate Tags')

        # Concatenate final string
        input_text = subject_type + "; " + ticket_body

        # Form submission
        if submit_button and (not subject_type or not ticket_body):
            st.warning('Please fill in both Subject Type and Ticket Body.')
        elif submit_button and (subject_type and ticket_body):
            with st.spinner('Loading Ticket Tags...'):

                # Load Dataset
                df = pd.read_csv("dependencies/fewshot_3final.csv") # Examples for few-shot inferencing (switch, if needed)
                df = df.rename(columns=lambda x: x.strip())

                # Globals
                global value_1, value_2, value_3, value_4
                global rationale_1, rationale_2, rationale_3, rationale_4

                # Criteria
                ticket_type_crit = """
                Question: Inquiries or clarifications about functionalities, how to use features, or general information requests not directly related to issues or disruptions.
                Problem: Reports of malfunctions, errors, or unexpected behavior in the system that adversely affects the user's ability to utilize the service or product effectively.
                Task: Requests for specific actions such as configurations, setups, modifications, or the processing of standard procedures.
                Enhancement: Suggestions for improving existing features or adding new functionalities that can enhance the user experience or product capabilities.
                Non Support: Tickets that do not pertain to specific support issues or queries, including spam, test messages, or irrelevant communications.
                """

                ticket_priority_crit = """
                Normal: Routine inquiries or requests that do not require immediate action. These tickets can be resolved within standard response times without significant impact on customer operations or satisfaction.
                Low: Tickets that have minor impact on operations and do not require immediate attention. These can be scheduled for resolution according to standard workflows and do not require urgent follow-up.
                High: Tickets that affect key operations or have a significant impact on user experience. These require prompt attention and resolution to mitigate impact but are not immediately threatening to business continuity or critical operations.
                Urgent: Issues causing critical service disruption or potential significant financial loss. These require immediate resolution to prevent extensive impact on business operations or customer satisfaction.
                """

                product_type_crit = """
                Sprout HR: Tickets related to the comprehensive human resources management system designed for employee data tracking, leave and benefits administration, compliance with labor laws, and other HR functions. This includes issues with setting up employee profiles, managing leave requests, and accessing HR reports.
                Sprout Payroll: Tickets concerning the payroll management system focused on automating payroll calculations, generating payslips, managing tax obligations, and other payroll-related processes. This covers problems with tax calculation accuracy, payroll processing errors, and configuration of payroll settings.
                Sprout Instacash: Tickets associated with the short-term loan facility offered to employees directly via the platform, covering loan application processes, approval status updates, repayment issues, and eligibility queries.
                Sprout Performance+: Tickets related to the employee performance management module that helps organizations set performance goals, conduct evaluations, and manage feedback. This includes issues related to goal setting functionalities, performance tracking discrepancies, and report generation.
                Sprout Mobile: Tickets dealing with the mobile application extensions of Sprout's products, focusing on user interface issues, mobile app crashes, feature accessibility, and synchronization problems between desktop and mobile platforms.
                Sprout Insight: Tickets focusing on the advanced analytics and reporting tool that provides business intelligence solutions for HR data, including detailed analytics on workforce statistics, trend analysis, and custom report issues.
                Sprout Ecosystem: Tickets that address interactions and integrations between various Sprout products, focusing on seamless data flow, user experience across platforms, and integration issues that affect multiple components of the Sprout ecosystem.
                Sprout Pulse: Tickets related to the tools for measuring and enhancing employee engagement and organizational health, such as survey distribution problems, analysis of employee feedback, and issues with deploying engagement initiatives.
                """

                prompt1 = f"""
                Look at the information from '''{df}'''. Train yourself on the data.
                Understand the relationships between the columns, rows, and how the values are correspond. 
                These are customer complaints that are categorized into certain tags, specificially: 
                Ticket Type, Ticket Priority, Module, and Product.

                Now, I want you to predict the 4 different labels for a new set of client complaint.
                Please provide the tags of the following context:
                '''{input_text}'''. If the screenshot context '''{screenshot_text}''' 
                is not empty, use this as context also.

                After summarizing and analyzing the text, please classify 
                the ticket with the following labels:

                - Ticket Type (Use criteria from '''{ticket_type_crit}'''): 
                - Ticket Priority (Use criteria from '''{ticket_priority_crit}): 
                - Module (Use context-based approach and options below. Only get from the options in '''{module}'''.): 
                - Product (Use criteria from '''{product_type_crit}'''):

                The FINAL/ONLY CONTENT OUTPUT should be in a Python list format, from product, priority, complaint, and support.
                Example: ['Question', 'Normal', 'SSO', 'Sprout HR']

                These must all be based from the list of '''{type}''', '''{priority}''', '''{module}''', and '''{product}'''.
                Base this on 
                """
                
                response = client.chat.completions.create(
                    model= os.getenv("LLM_DEPLOYMENT_NAME"),
                    messages=[
                        {"role": "system", "content": "You are a large language model trained by OpenAI, and your task is to only provide the Python list needed."},
                        {"role": "user", "content": prompt1}
                    ]
                )
                ticket_output = response.choices[0].message.content
                tag_list = ast.literal_eval(ticket_output)
                print(tag_list)

                value_1 = tag_list[0]
                value_2 = tag_list[1]
                value_3 = tag_list[2]
                value_4 = tag_list[3]

                # Create an empty list for accuracy
                rationale_list = []

                prompt2 = f"""
                Now, based on the criteria presented below, explain the reason for 
                the given category tag for '''{value_1}'''. The context for your explanation
                will come from '''{input_text}'''. Keep it direct and concise for the user.

                Please use the criteria found in '''{ticket_type_crit}'''.
                """
                
                rat_output_1 = client.chat.completions.create(
                    model= os.getenv("LLM_DEPLOYMENT_NAME"),
                    messages=[
                        {"role": "system", "content": "You will provide the rationale to the prompt. Provide in only 3 sentences."},
                        {"role": "user", "content": prompt2}
                    ]
                )
                rat_output_1 = rat_output_1.choices[0].message.content
                rationale_list.append(rat_output_1)

                prompt3 = f"""
                Now, based on the criteria presented below, explain the reason for 
                the given category tag for '''{value_2}'''. The context for your explanation
                will come from '''{input_text}'''. Keep it direct and concise for the user.

                Please use the criteria found in '''{ticket_priority_crit}'''.
                """

                rat_output_2 = client.chat.completions.create(
                    model= os.getenv("LLM_DEPLOYMENT_NAME"), 
                    messages=[
                        {"role": "system", "content": "You will provide the rationale to the prompt. Provide in only 3 sentences."},
                        {"role": "user", "content": prompt3}
                    ]
                )
                rat_output_2 = rat_output_2.choices[0].message.content
                rationale_list.append(rat_output_2)

                prompt4 = f"""
                Now, based on the criteria presented below, explain the reason for 
                the given category tag for '''{value_3}'''. The context for your explanation
                will come from '''{input_text}'''. Keep it direct and concise for the user.
                """

                rat_output_3 = client.chat.completions.create(
                    model= os.getenv("LLM_DEPLOYMENT_NAME"), 
                    messages=[
                        {"role": "system", "content": "You will provide the rationale to the prompt. Provide in only 3 sentences."},
                        {"role": "user", "content": prompt4}
                    ]
                )
                rat_output_3 = rat_output_3.choices[0].message.content
                rationale_list.append(rat_output_3)

                prompt5 = f"""
                Now, based on the criteria presented below, explain the reason for 
                the given category tag for '''{value_4}'''. The context for your explanation
                will come from '''{input_text}'''. Keep it direct and concise for the user.

                Please use the criteria found in '''{product_type_crit}'''.
                """

                rat_output_4 = client.chat.completions.create(
                    model= os.getenv("LLM_DEPLOYMENT_NAME"), 
                    messages=[
                        {"role": "system", "content": "You will provide the rationale to the prompt. Provide in only 3 sentences."},
                        {"role": "user", "content": prompt5}
                    ]
                )
                rat_output_4 = rat_output_4.choices[0].message.content
                rationale_list.append(rat_output_4)

                # Trim whitespace from each element in the list
                final_rationale = [item.strip() for item in rationale_list]
                
                rationale_1 = final_rationale[0]
                rationale_2 = final_rationale[1]
                rationale_3 = final_rationale[2]
                rationale_4 = final_rationale[3]
                time.sleep(5)

            # Display table
            st.header('Ticket Labels')

            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("Ticket Type")
                st.code(value_1, language="python")
                # Unselected tags
                st.markdown("Unselected Tags")
                new_list = [item for item in type if item != value_1]
                st.code(new_list, language="txt")
                st.markdown(rationale_1)

            with col2:
                st.markdown("Module")
                st.code(value_3, language="python")
                st.markdown("Unselected Tags")
                new_list = [item for item in module if item != value_3]
                st.code(new_list, language="txt")
                st.markdown(rationale_3)

            col3, col4 = st.columns(2)

            with col3:
                st.markdown("Ticket Priority")
                st.code(value_2, language="python")
                # Unselected tags
                st.markdown("Unselected Tags")
                new_list = [item for item in priority if item != value_2]
                st.code(new_list, language="txt")
                st.markdown(rationale_2)

            with col4:
                st.markdown("Product")
                st.code(value_4, language="python")
                # Unselected tags
                st.markdown("Unselected Tags")
                new_list = [item for item in product if item != value_4]
                st.code(new_list, language="txt")
                st.markdown(rationale_4)

            # Space below the tables
            st.markdown("""
            """)

# Run the Streamlit app
if __name__ == '__main__':
    main()