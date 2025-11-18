import { useState } from "react";
import api from "../../api";

export default function Enable2FA() {
  // Initial state is null, so "Enable 2FA" button shows first
  const [qrCode, setQrCode] = useState(null);
  const [secret, setSecret] = useState(null);
  const [code, setCode] = useState("");
  const [verified, setVerified] = useState(false);

  const enable2FA = async () => {
    // TEMPORARY: This alert will confirm if the function is being called
    alert("Enable 2FA button clicked!");
    try {
      const res = await api.post("/security/enable-2fa");
      // TEMPORARY: Log the full response data to the browser console
      console.log("Backend response for enable-2fa:", res.data);
      setQrCode(res.data.qr_code);
      setSecret(res.data.secret);
      // TEMPORARY: Log the qrCode state immediately after setting it
      console.log("qrCode state after setQrCode:", res.data.qr_code);
    } catch (error) {
      console.error("Error enabling 2FA:", error); // Log any network/API errors
      alert("Failed to enable 2FA. Please try again.");
    }
  };

  const verifyCode = async () => {
    try {
      const res = await api.post("/security/verify-2fa", { code });
      if (res.data.success) {
        setVerified(true);
        alert("2FA Enabled Successfully!");
      } else {
        alert("Invalid Code!"); // Explicitly handle false success from backend
      }
    } catch (error) {
      console.error("Error verifying 2FA:", error); // Log any network/API errors
      alert("Error verifying code. Please try again.");
    }
  };

  return (
    <div className="p-4 border rounded-lg">
      {!qrCode ? ( // If qrCode is null, show the "Enable 2FA" button
        <button
          onClick={enable2FA}
          className="bg-blue-500 text-white px-4 py-2 rounded"
        >
          Enable 2FA
        </button>
      ) : ( // Otherwise (if qrCode has a value), show the QR code and verification input
        <div>
          <p>Scan this QR Code in Google Authenticator:</p>
          {/* TEMPORARY VISUAL INDICATOR: This text should always appear if the QR code section is rendering */}
          <p style={{ color: 'blue', fontSize: '20px', fontWeight: 'bold' }}>--- QR CODE SHOULD BE HERE ---</p>
          <img
            // Fallback to a tiny transparent image if qrCode is unexpectedly null, though it shouldn't be here
            src={qrCode || "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="}
            alt="QR Code"
            // TEMPORARY OVERRIDE STYLES: This forces a red border and specific size for visibility
            style={{ border: '5px solid red', width: '250px', height: '250px', display: 'block', margin: '10px 0' }}
          />
          <input
            type="text"
            placeholder="Enter 6-digit code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="border p-2 mt-2"
          />
          <button
            onClick={verifyCode}
            className="bg-green-500 text-white px-4 py-2 rounded ml-2"
          >
            Verify
          </button>
          {verified && (
            <p className="text-green-600 mt-2">2FA is now active!</p>
          )}
        </div>
      )}
    </div>
  );
}
