# visualize_graph.py

import os
from graph import app

def save_graph_image():
    """
    Saves a visualization of the LangGraph structure to the 'assets' folder.
    """
    try:
        # Create the 'assets' directory if it doesn't exist
        os.makedirs("assets", exist_ok=True)
        
        # Get the graph diagram as PNG bytes
        graph_image = app.get_graph().draw_mermaid_png()
        
        # Define the output path
        output_path = os.path.join("assets", "research_graph.png")
        
        # Write the bytes to a file
        with open(output_path, "wb") as f:
            f.write(graph_image)
            
        print(f"✓ Graph image saved to {output_path}")
        
    except ImportError as e:
        print("\n" + "="*60)
        print("ERROR: Required package not found.")
        print("To visualize the graph, install:")
        print("="*60 + "\n")
        
    except AttributeError:
        print("\n" + "="*60)
        print("Trying alternative visualization method...")
        try:
            # Try the mermaid approach without PNG
            graph_repr = app.get_graph().draw_mermaid()
            output_path = os.path.join("assets", "research_graph.mmd")
            
            with open(output_path, "w") as f:
                f.write(graph_repr)
            
            print(f"✓ Graph saved as Mermaid diagram to {output_path}")
            print("You can view this at: https://mermaid.live/")
            
        except Exception as e2:
            print(f"Could not save graph: {e2}")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"An error occurred while generating the graph: {e}")

if __name__ == "__main__":
    save_graph_image()