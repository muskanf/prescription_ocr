// UMD bundles already loaded in index.html
const {
  Box, Container, Typography, Button, Stack, Paper,
  Card, CardContent, CircularProgress, Link
} = MaterialUI;

const { spawn } = require('child_process');
const fs = require('fs');


function App() {
  const [step, setStep] = React.useState("welcome");   // welcome | instructions | upload
  const [data, setData] = React.useState(null);
  const [loading, setLoading] = React.useState(false);

  // ---------- OCR pipeline ----------
  const runOCR = (filePath) => {
    setLoading(true);
    setData(null);

    const path = require('path')
    const script = path.join(__dirname, 'extract_rx.py')
    const py = spawn('python', [script, filePath])
    let output = '';

    py.stdout.on('data', chunk => output += chunk.toString());
    py.stdout.on('end', () => {
      try { setData(JSON.parse(output)); }
      catch { alert("Could not parse OCR output."); }
      setLoading(false);
    });
    py.stderr.on('data', err => console.error(err.toString()));
  };

  // ---------- Handlers ----------
  const handleFile = (file) => {
    if (!file) return;
    runOCR(file.path);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    handleFile(e.dataTransfer.files[0]);
  };

  const handleSend = () => {
    if (!data) return;
    fs.appendFileSync('output/output.csv', JSON.stringify(data) + '\n');
    alert("Exported to CSV!");
  };

  // ---------- Reusable chunks ----------
  const hero = (title, subtitle, actions) =>
    React.createElement(Container, {
      maxWidth: "md",
      sx: { pt: 12, pb: 8, textAlign: "center" }
    }, [
      React.createElement(Typography, { variant: "h3", component: "h1", gutterBottom: true }, title),
      React.createElement(Typography, { variant: "h6", color: "text.secondary", mb: 4 }, subtitle),
      React.createElement(Stack, { direction: "row", spacing: 2, justifyContent: "center" }, actions)
    ]);

  // ---------- UI per step ----------
  if (step === "welcome") {
    return hero(
      "Welcome to m3dswft",
      "AI-powered prescription intake in seconds.",
      [
        React.createElement(Button, {
          variant: "contained", size: "large",
          onClick: () => setStep("instructions")
        }, "Start")
      ]
    );
  }

  if (step === "instructions") {
    return hero(
      "How it Works",
      "1. Drag a scanned prescription or click Upload\n2. AI reads patient, meds & sig codes\n3. Review & send to RxConnect",
      [
        React.createElement(Button, {
          variant: "outlined", size: "large",
          onClick: () => setStep("upload")
        }, "Proceed to Upload"),
        React.createElement(Link, {
          href: "#", underline: "hover",
          onClick: () => setStep("welcome")
        }, "Back")
      ]
    );
  }

  // ---------- Upload / OCR screen ----------
  return React.createElement(Container, { maxWidth: "md", sx: { pt: 6, pb: 10 } }, [

    React.createElement(Stack, { spacing: 3 }, [

      // Drop zone + upload button
      React.createElement(Paper, {
        elevation: 3,
        onDrop: handleDrop,
        onDragOver: e => e.preventDefault(),
        sx: {
          p: 5, textAlign: "center", border: "2px dashed #90caf9",
          backgroundColor: "#e3f2fd", cursor: "pointer"
        }
      }, "📄  Drag & Drop Prescription Here"),

      React.createElement("input", {
        id: "fileInput", type: "file", accept: ".pdf,.png,.jpg,.jpeg",
        style: { display: 'none' },
        onChange: e => handleFile(e.target.files[0])
      }),
      React.createElement(Button, {
        variant: "contained",
        onClick: () => document.getElementById('fileInput').click()
      }, "Choose File"),

      // Loading spinner
      loading && React.createElement(Box, { textAlign: "center" },
        React.createElement(CircularProgress, null)
      ),

      // Result card
      data && React.createElement(Card, { id: "results-card" },
        React.createElement(CardContent, null, [

          React.createElement(Typography, { variant: "h6" },
            `Patient: ${data.name || '—'}`),

          React.createElement(Typography, { variant: "body1" },
            `DOB: ${data.dob || '—'}`),

          React.createElement(Typography, { variant: "subtitle1", sx: { mt: 2 } },
            "Medication"),

          React.createElement(Typography, { variant: "body1" },
            `${data.medication || '—'}${data.dosage ? ' ' + data.dosage : ''}`),

          React.createElement(Typography, { variant: "body2", sx: { mt: 1 } },
            `Frequency: ${data.frequency || '—'}`)
        ])
      ),

      // Send button
      React.createElement(Button, {
        variant: "contained",
        disabled: !data,
        onClick: handleSend
      }, "Parse Prescription")
    ]),

    // Back link
    React.createElement(Box, { textAlign: "center", mt: 4 },
      React.createElement(Link, {
        href: "#", underline: "hover",
        onClick: () => setStep("instructions")
      }, "Back to Instructions")
    )
  ]);
}

ReactDOM.createRoot(document.getElementById("root"))
  .render(React.createElement(App));

