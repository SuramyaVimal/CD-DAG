import React, { useState } from 'react';
import axios from 'axios';

export default function App() {
  const [expression, setExpression] = useState('');
  const [dagImage, setDagImage] = useState(null);
  const [optimalSequence, setOptimalSequence] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const generateDAG = async () => {
    setLoading(true);
    setError(null);
    setDagImage(null);
    setOptimalSequence([]);
    try {
      const res = await axios.post('http://localhost:5000/generate-dag', {
        expression,
      });
      setDagImage(`data:image/png;base64,${res.data.dag_image}`);
      setOptimalSequence(res.data.optimal_sequence);
    } catch (err) {
      setError('Error generating DAG. Please check your TAC input.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-100 to-purple-100 flex flex-col items-center p-6">
      <div className="bg-white shadow-2xl rounded-2xl p-8 w-full max-w-2xl">
        <h1 className="text-3xl font-bold text-center mb-4 text-purple-700">DAG Visualizer</h1>
        
        <p className="text-center text-gray-600 mb-4 font-medium">
          Enter your Three Address Code:
        </p>

        <textarea
          value={expression}
          onChange={(e) => setExpression(e.target.value)}
          className="w-full p-3 border border-gray-300 rounded-xl mb-4 focus:outline-none focus:ring-2 focus:ring-purple-400"
          placeholder={`t1 = a + b\nt2 = t1 * c\nt3 = t2 - d`}
          rows={6}
        />

        <button
          onClick={generateDAG}
          className="w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-3 rounded-xl transition duration-200"
        >
          {loading ? 'Generating...' : 'Generate DAG & Optimal Sequence'}
        </button>

        {error && <p className="text-red-600 mt-4 text-center">{error}</p>}

        {optimalSequence.length > 0 && (
          <p className="text-center text-green-800 mt-6 text-lg">
            <strong>Optimal Sequence:</strong> <code>{optimalSequence.join(', ')}</code>
          </p>
        )}

        {dagImage && (
          <div className="mt-6 text-center">
            <h2 className="text-xl font-semibold text-purple-700 mb-2">DAG Visualization</h2>
            <img src={dagImage} alt="DAG" className="mx-auto border-4 border-purple-200 rounded-xl shadow-md" />
          </div>
        )}
      </div>
    </div>
  );
}
