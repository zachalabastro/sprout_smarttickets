# Install modules
import os
import time
import streamlit as st
from st_copy_to_clipboard import st_copy_to_clipboard
import ast
import pandas as pd
import openai
from PIL import Image
import pytesseract
import PyPDF2

# Load file upload folder
upload_dir = "file_upload" # Replace accordingly
output_dir = "file_output" # Replace accordingly
output_file = "file_output/final_output.txt" # Replace accordingly
os.makedirs(upload_dir, exist_ok=True)

# Load Dataset
df = pd.read_csv("dependencies/synthetic_data.csv")
df = df.rename(columns=lambda x: x.strip())

# Concatenate Ticket Subject and Body
df['Complete Ticket'] = df['Client Complaint'].str.cat(df['Ticket Body'], sep='; ')
df.insert(loc=2, column='Complete Ticket', value=df.pop('Complete Ticket'))

# Turn int into a str
df['Support Level'] = df['Support Level'].astype(str)

# Load Dataset labels
product = df['Type of Product'].unique()
priority = df['Priority'].unique()
type_complaint = df['Type of Complaint'].unique()
support = df['Support Level'].unique()

# Azure OpenAI Key
openai.api_type = "azure"
openai.api_version = "2024-02-01" 
openai.api_base = os.environ.get("AZURE_OPENAI_ENDPOINT")
openai.api_key = os.environ.get("AZURE_OPENAI_KEY")

# Define the Streamlit app layout
def main():
    st.title('Customer Advocacy SmartTickets')
    st.markdown(
        """
        <style>
        .form-container {
            width: 75%;
            max-width: 1000px;
            padding: 20px;
            padding-top: 15px;
            border: 1px solid #ccc;
            border-radius: 8px;
            background-color: #9AB379;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            align-items: center;
            display: flex;
            flex-direction: column;
            margin: 0px;
            margin-bottom: 20px; /* Add margin-bottom for space */
        }

        .input-field,
        .input-field-long {
            width: calc(100%); /* 20px padding and 1px border on each side */
            padding: 10px;
            margin-top: 15px;
            margin-bottom: 15px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }

        .input-field-long {
            min-height: 150px; /* Or any other height */
        }

        .submit-button {
            width: 100%;
            padding: 10px;
            border: none;
            border-radius: 4px;
            background-color: #F5F5F5;
            color: #000;
            cursor: pointer;
            box-sizing: border-box;
            transition: background-color 0.3s ease, color 0.3s ease;
        }

        .submit-button:hover {
            background-color: #444F37;
            color: #f4f4f4;
        }

        .header {
            background-color: #444F37;
            padding: 5px;
            margin-top: 0px;
            margin-bottom: 15px;
            width: 100%;
            border-radius: 8px;
        }

        .header h1 {
            text-align: center;
            color: white;
            margin-top: 2.5px;
            margin-bottom: 2.5px;
        }
        </style>

         <script>
            function copyToClipboard(btn) {
                var text = btn.closest('tr').children[1].innerText;
                var dummy = document.createElement("textarea");
                document.body.appendChild(dummy);
                dummy.value = text;
                dummy.select();
                document.execCommand("copy");
                document.body.removeChild(dummy);
            }
        </script>
        """,
        unsafe_allow_html=True
    )

    # Form inputs
    with st.form(key='my_form'):
        st.header('Submit a Ticket')
        st.markdown("<hr>", unsafe_allow_html=True)

        # Text input
        # File uploads
        subject_type = st.text_input('Subject Type', max_chars=100)
        ticket_body = st.text_area('Ticket Body', height=150)   
        uploaded_files = st.file_uploader('Upload Screenshots', type=["jpg", "pdf", "png", "jpeg"], accept_multiple_files=True)
        
        # Upload file button (not a requirement)
        upload_file_button = st.form_submit_button(label='Upload Files')

        # Upload the files selected
        if upload_file_button:
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
            global final_context
            final_context = context.read()

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
                prompt = f"""
                Look at the information from '''{df}'''. Understand the relationships between the
                columns, rows, and how the values are correspond to each other. These are customer
                complaints that are categorized into certain tags, specificially: Type of Product, Priority,
                Type of Complaint, and Support Level. Identify why, and train yourself on the distinctions.

                Now, I want you to predict the 4 different labels for a new set of client complaint.
                Please provide the tags of the following context:
                '''{input_text}'''. If the screenshot context '''{final_context}''' 
                is not empty, use this as context also.

                After summarizing and analyzing the text, please classify 
                the ticket with the following labels:

                - Type of Product: 
                - Priority: 
                - Type of Complaint: 
                - Support Level:

                The FINAL/ONLY CONTENT OUTPUT should be in a Python list format, from product, priority, complaint, and support.
                Example: ['GPay', 'Not Urgent', 'Payment Issue', '4']

                These must all be based from the list of '''{product}''', '''{priority}''', '''{type_complaint}''', and '''{support}'''.
                """
                
                ticket_output = openai.ChatCompletion.create(
                    engine=os.environ.get("LLM_DEPLOYMENT_NAME"),
                    messages=[
                        {"role": "system", "content": "Assistant is a large language model trained by OpenAI, and will only output a list format in Python, without words before or after the list."},
                        {"role": "user", "content": prompt}
                    ]
                )
                ticket_output = ticket_output['choices'][0]['message']['content']
                tag_list = ast.literal_eval(ticket_output)

                global value_1, value_2, value_3, value_4
                value_1 = tag_list[0]
                value_2 = tag_list[1]
                value_3 = tag_list[2]
                value_4 = tag_list[3]

                product_crit = f"""
                Mobile Payments: GCash allows users to make mobile payments securely and conveniently.
                GSave: A high-yield savings account that offers users options between CIMB Bank Philippines, BPI, and Maybank Philippines.
                GCredit: A revolving mobile credit line initially powered by Fuse Lending, later transferred to CIMB Bank.
                GCash Padala: A remittance service available to both app users and non-app users through partner outlets.
                GCash Jr.: Designed for users aged 7 to 17, offering a tailored experience.
                Double Safe: A security feature requiring facial identification from customers to enhance safety.
                GForest: Allows users to collect green energy by engaging in eco-friendly activities.
                GLife: An app where users can shop for various products from their favorite brands.
                KKB: Enables users to split bills with friends, even if they do not have GCash.
                GGives: Offers a buy now, pay later service with flexible payments.
                GInsure: Provides affordable insurance options within the GCash app.
                GCash Pera Outlet: Allows individuals to earn money by becoming a GCash Pera Outlet.
                GCredit: Provides users with a credit line for extended budget flexibility.
                GLoan: Offers pre-approved access to cash loans instantly without collateral.
                GFunds: Enables users to invest in funds managed by partner providers.
                GSave: A feature that helps users save for the future conveniently within the GCash app.
                """

                priority_crit = f"""
                Urgent: Issues causing critical service disruption or financial loss.
                Not Urgent: Non-critical issues with no immediate impact on operations or customer satisfaction.
                Normal: Routine inquiries or requests not requiring immediate attention or action.
                """

                complaint_crit = f"""
                Account Issue: Customer account-related problems with significant impact.
                Transaction Failure: Failures in financial transactions with substantial consequences.
                Technical Issue: Technical problems affecting the service or application.
                Claim Issue: Disputes or problems related to claims processing.
                Account Access: Difficulties accessing the customer's account or system.
                Billing Error: Errors in billing or invoicing processes.
                Application Error: Errors or malfunctions within the application or software.
                Payment Issue: Issues related to payment processing or transactions.
                Disbursement Issue: Problems with disbursement or distribution of funds.
                Service Issue: General issues with the service provided.
                Activation Error: Errors during the activation process of a service or product.
                """

                support_crit = f"""
                1 - Requires extensive specialized support and engineering assistance.
                2 - Requires minor specialized support from engineering or technical staff.
                3 - Requires assistance from experienced Customer Advocacy (CA) members.
                4 - Can be handled by any member of Customer Advocacy (CA) team.
                """

                # Create an empty list for accuracy
                rationale_list = []

                rat_prompt_1 = f"""
                Now, based on the criteria presented below, explain the reason for 
                such given category tag: '''{value_1}'''. The context for your explanation
                will come from '''{input_text}'''.

                Explanation Format Sample: Ticket was given product tag 'GCredit' because it primarily revolves around mobile credit concerns raised.
                Do NOT include any commas (",") in the explanataion. Be straightforward in producing the sentence.

                Here is the criteria as basis for your explanation:
                '''{product_crit}'''
                """

                rat_output_1 = openai.ChatCompletion.create(
                    engine=os.environ.get("LLM_DEPLOYMENT_NAME"),
                    messages=[
                        {"role": "system", "content": "Assistant is a large language model trained by OpenAI."},
                        {"role": "user", "content": rat_prompt_1}
                    ]
                )
                rat_output_1 = rat_output_1['choices'][0]['message']['content']
                rationale_list.append(rat_output_1)

                rat_prompt_2 = f"""
                Now, based on the criteria presented below, explain the reason for 
                such given category tag: '''{value_2}'''. The context for your explanation
                will come from '''{input_text}'''.

                Explanation Format Sample: Ticket was given product tag 'GCredit' because it primarily revolves around mobile credit concerns raised.
                Do NOT include any commas (",") in the explanataion. Be straightforward in producing the sentence.

                Here is the criteria as basis for your explanation:
                '''{priority_crit}'''
                """

                rat_output_2 = openai.ChatCompletion.create(
                    engine=os.environ.get("LLM_DEPLOYMENT_NAME"),
                    messages=[
                        {"role": "system", "content": "Assistant is a large language model trained by OpenAI."},
                        {"role": "user", "content": rat_prompt_2}
                    ]
                )
                rat_output_2 = rat_output_2['choices'][0]['message']['content']
                rationale_list.append(rat_output_2)

                rat_prompt_3 = f"""
                Now, based on the criteria presented below, explain the reason for 
                such given category tag: '''{value_3}'''. The context for your explanation
                will come from '''{input_text}'''.

                Explanation Format Sample: Ticket was given product tag 'GCredit' because it primarily revolves around mobile credit concerns raised.
                Do NOT include any commas (",") in the explanataion. Be straightforward in producing the sentence.

                Here is the criteria as basis for your explanation:
                '''{complaint_crit}'''
                """

                rat_output_3 = openai.ChatCompletion.create(
                    engine=os.environ.get("LLM_DEPLOYMENT_NAME"),
                    messages=[
                        {"role": "system", "content": "Assistant is a large language model trained by OpenAI."},
                        {"role": "user", "content": rat_prompt_3}
                    ]
                )
                rat_output_3 = rat_output_3['choices'][0]['message']['content']
                rationale_list.append(rat_output_3)

                rat_prompt_4 = f"""
                Now, based on the criteria presented below, explain the reason for 
                such given category tag: '''{value_4}'''. The context for your explanation
                will come from '''{input_text}'''.

                Explanation Format Sample: Ticket was given product tag 'GCredit' because it primarily revolves around mobile credit concerns raised.
                Do NOT include any commas (",") in the explanataion. Be straightforward in producing the sentence.

                Here is the criteria as basis for your explanation:
                '''{support_crit}'''
                """

                rat_output_4 = openai.ChatCompletion.create(
                    engine=os.environ.get("LLM_DEPLOYMENT_NAME"),
                    messages=[
                        {"role": "system", "content": "Assistant is a large language model trained by OpenAI."},
                        {"role": "user", "content": rat_prompt_4}
                    ]
                )
                rat_output_4 = rat_output_4['choices'][0]['message']['content']
                rationale_list.append(rat_output_4)

                # Trim whitespace from each element in the list
                final_rationale = [item.strip() for item in rationale_list]
                
                global rationale_1, rationale_2, rationale_3, rationale_4
                rationale_1 = final_rationale[0]
                rationale_2 = final_rationale[1]
                rationale_3 = final_rationale[2]
                rationale_4 = final_rationale[3]
                time.sleep(5)

            # Display table
            st.header('Ticket Labels')

            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("Type of Product")
                st.code(value_1, language="python")
                st.markdown(rationale_1)

            with col2:
                st.markdown("Type of Complaint")
                st.code(value_3, language="python")
                st.markdown(rationale_3)

            col3, col4 = st.columns(2)

            with col3:
                st.markdown("Priority Level")
                st.code(value_2, language="python")
                st.markdown(rationale_2)

            with col4:
                st.markdown("Support Level")
                st.code(value_4, language="python")
                st.markdown(rationale_4)

            # Space below the tables
            st.markdown("""
            """)

# Run the Streamlit app
if __name__ == '__main__':
    main()