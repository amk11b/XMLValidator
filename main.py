from flask import Flask, request, render_template, jsonify, session
import xmlschema
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.secret_key = os.urandom(24)  # Required for session management


def init_session():
    if 'schemas' not in session:
        session['schemas'] = {}


def save_schema(file):
    """Save uploaded schema and return its ID"""
    filename = secure_filename(file.filename)
    schema_id = str(uuid.uuid4())
    schema_path = os.path.join(app.config['UPLOAD_FOLDER'], f"schema_{schema_id}.xsd")
    file.save(schema_path)

    # Store schema info in session
    if 'schemas' not in session:
        session['schemas'] = {}

    session['schemas'][schema_id] = {
        'name': filename,
        'path': schema_path,
        'timestamp': datetime.now().isoformat()
    }
    session.modified = True
    return schema_id


def validate_xml_with_schema(xml_path, schema_path):
    try:
        schema = xmlschema.XMLSchema(schema_path)
        schema.validate(xml_path)
        return True, "XML is valid according to the schema"
    except Exception as e:
        return False, str(e)


@app.route('/', methods=['GET'])
def index():
    init_session()
    return render_template('index.html', schemas=session.get('schemas', {}))


@app.route('/upload-schema', methods=['POST'])
def upload_schema():
    if 'schema_file' not in request.files:
        return jsonify({'success': False, 'message': 'No schema file provided'})

    schema_file = request.files['schema_file']

    if schema_file.filename == '':
        return jsonify({'success': False, 'message': 'No schema file selected'})

    if not schema_file.filename.lower().endswith('.xsd'):
        return jsonify({'success': False, 'message': 'File must be an XSD schema'})

    try:
        schema_id = save_schema(schema_file)
        schema_info = session['schemas'][schema_id]

        return jsonify({
            'success': True,
            'schema_id': schema_id,
            'schema_name': schema_info['name']
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/validate', methods=['POST'])
def validate():
    if 'xml_file' not in request.files:
        return jsonify({'success': False, 'message': 'XML file is required'})

    xml_file = request.files['xml_file']
    schema_id = request.form.get('schema_id')

    if xml_file.filename == '':
        return jsonify({'success': False, 'message': 'No XML file selected'})

    if not xml_file.filename.lower().endswith('.xml'):
        return jsonify({'success': False, 'message': 'File must be an XML file'})

    if not schema_id or schema_id not in session.get('schemas', {}):
        return jsonify({'success': False, 'message': 'Please select a valid schema'})

    try:
        # Save XML file
        xml_filename = secure_filename(xml_file.filename)
        xml_path = os.path.join(app.config['UPLOAD_FOLDER'], xml_filename)
        xml_file.save(xml_path)

        # Get schema path
        schema_path = session['schemas'][schema_id]['path']

        # Validate XML
        is_valid, message = validate_xml_with_schema(xml_path, schema_path)

        # Clean up XML file
        os.remove(xml_path)

        return jsonify({
            'success': True,
            'isValid': is_valid,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        # Clean up XML file if it exists
        if 'xml_path' in locals() and os.path.exists(xml_path):
            os.remove(xml_path)

        return jsonify({
            'success': False,
            'message': f'Error processing files: {str(e)}'
        })


@app.route('/remove-schema/<schema_id>', methods=['POST'])
def remove_schema(schema_id):
    if schema_id in session.get('schemas', {}):
        schema_path = session['schemas'][schema_id]['path']
        if os.path.exists(schema_path):
            os.remove(schema_path)
        del session['schemas'][schema_id]
        session.modified = True
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Schema not found'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=os.getenv('PORT', 10000))