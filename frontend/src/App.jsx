import CameraPanel from "./components/CameraPanel";
import TrafficMap from "./components/TrafficMap";

function App() {
    return (
        <main>
            <h1>Louisiana Live Traffic</h1>
            <TrafficMap />
            <CameraPanel />
        </main>
    );
}

export default App;
