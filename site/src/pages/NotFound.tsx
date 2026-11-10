import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <>
      <h1>Not found</h1>
      <p><Link to="/">Go home</Link></p>
    </>
  );
}
