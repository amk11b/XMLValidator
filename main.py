from flask import Flask, request, render_template, jsonify
import xmlschema
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp'  # Render allows /tmp for file operations
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size


def validate_xml_with_schema(xml_path, xsd_path):
    try:
        schema = xmlschema.XMLSchema(xsd_path)
        schema.validate(xml_path)
        return True, "XML is valid according to the schema"
    except Exception as e:
        return False, str(e)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/validate', methods=['POST'])
def validate():
    # Check if both files are present
    if 'xml_file' not in request.files or 'schema_file' not in request.files:
        return jsonify({'success': False, 'message': 'Both XML and Schema files are required'})

    xml_file = request.files['xml_file']
    schema_file = request.files['schema_file']

    # Check if both files were selected
    if xml_file.filename == '' or schema_file.filename == '':
        return jsonify({'success': False, 'message': 'Please select both XML and Schema files'})

    # Validate file extensions
    if not xml_file.filename.lower().endswith('.xml'):
        return jsonify({'success': False, 'message': 'First file must be an XML file'})

    if not schema_file.filename.lower().endswith('.xsd'):
        return jsonify({'success': False, 'message': 'Second file must be an XSD schema file'})

    try:
        # Save both files
        xml_filename = secure_filename(xml_file.filename)
        schema_filename = secure_filename(schema_file.filename)

        xml_path = os.path.join(app.config['UPLOAD_FOLDER'], xml_filename)
        schema_path = os.path.join(app.config['UPLOAD_FOLDER'], schema_filename)

        xml_file.save(xml_path)
        schema_file.save(schema_path)

        # Validate XML against Schema
        is_valid, message = validate_xml_with_schema(xml_path, schema_path)

        # Clean up uploaded files
        os.remove(xml_path)
        os.remove(schema_path)

        return jsonify({
            'success': True,
            'isValid': is_valid,
            'message': message
        })

    except Exception as e:
        # Clean up files in case of error
        if 'xml_path' in locals() and os.path.exists(xml_path):
            os.remove(xml_path)
        if 'schema_path' in locals() and os.path.exists(schema_path):
            os.remove(schema_path)

        return jsonify({
            'success': False,
            'message': f'Error processing files: {str(e)}'
        })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.getenv('PORT', 10000))